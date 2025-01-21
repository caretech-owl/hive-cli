import datetime
import logging
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.types import (
    PrivateKeyTypes,
)
from cryptography.x509.oid import NameOID

from hive_cli.config import load_settings

_LOGGER = logging.getLogger(__name__)


def generate_private_key(passphrase: str, output_path: Path) -> None:
    if not passphrase:
        msg = "Passphrase must not be empty."
        raise ValueError(msg)
    exponent = 65537
    key_size = 2048
    _LOGGER.debug(
        "Generating private key with public_exponent=%d and key_size%d."
        " Passphrase is %d characters long ...",
        exponent,
        key_size,
        len(passphrase),
    )
    key = rsa.generate_private_key(
        public_exponent=exponent,
        key_size=key_size,
    )

    # Write our key to disk for safe keeping
    with output_path.open("wb") as f:
        f.write(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.BestAvailableEncryption(
                    passphrase.encode()
                ),
            )
        )
    _LOGGER.debug("Private key written to %s.", output_path)


def load_private_key(passphrase: str, path: Path) -> PrivateKeyTypes:
    _LOGGER.debug("Attempt to load private key ...")
    if not path.exists():
        generate_private_key(passphrase, path)
    _LOGGER.debug("Loading private key from %s ...", path)
    with path.open("rb") as f:
        return serialization.load_pem_private_key(
            f.read(),
            password=passphrase.encode(),
        )


def get_sha256_fingerprint() -> str:
    settings = load_settings().server.ssl
    if not settings.cert_path.exists():
        _LOGGER.error("Certificate does not exist.")
        return
    with settings.cert_path.open("rb") as f:
        cert: x509.Certificate = x509.load_pem_x509_certificate(f.read())
    return cert.fingerprint(hashes.SHA256()).hex()


def generate_cert() -> None:
    settings = load_settings().server.ssl
    if settings.cert_path.exists():
        _LOGGER.debug("Certificate already exists.")
        return
    _LOGGER.info("Generating certificate ...")
    key = load_private_key(settings.passphrase, settings.key_path)
    if not isinstance(key, rsa.RSAPrivateKey):
        msg = "Private key is not a RSA private key."
        raise AssertionError(msg)
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, settings.country_name),
            x509.NameAttribute(
                NameOID.STATE_OR_PROVINCE_NAME, settings.state_or_province_name
            ),
            x509.NameAttribute(NameOID.LOCALITY_NAME, settings.locality_name),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, settings.organization_name),
            x509.NameAttribute(NameOID.COMMON_NAME, settings.common_name),
        ]
    )
    pub_key = key.public_key()
    if not isinstance(pub_key, rsa.RSAPublicKey):
        msg = "Public key is not a RSA public key."
        raise AssertionError(msg)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(pub_key)
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
        .not_valid_after(
            # Our certificate will be valid for 10 days
            datetime.datetime.now(datetime.timezone.utc)
            + datetime.timedelta(days=10)
        )
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName("localhost")]),
            critical=False,
            # Sign our certificate with our private key
        )
        .sign(key, hashes.SHA256())
    )
    # Write our certificate out to disk.
    _LOGGER.info("Certificate generated. Writing to %s ...", settings.cert_path)
    with settings.cert_path.open("wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
