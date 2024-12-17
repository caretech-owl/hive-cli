## v0.5.0 (2024-12-17)

### New feature:

- add repo list to frontend([`fce9eaf`](https://github.com/caretech-owl/hive-cli/commit/fce9eaf853a7dbd3875cca83e4cb8f810fb2b6d2)) (by Alexander Neumann)
- add list_files to styling([`29dc25e`](https://github.com/caretech-owl/hive-cli/commit/29dc25e4c9f893732176ef185f778984fc1bbcf5)) (by Alexander Neumann)
- reset repo or crate branch from local changes([`4d88d5e`](https://github.com/caretech-owl/hive-cli/commit/4d88d5e94b516af014478a972de16e6cfeabbda3)) (by Alexander Neumann)
- allow to create recipes and compose files from GUI([`cd6d955`](https://github.com/caretech-owl/hive-cli/commit/cd6d955176715b55e5781e5e0cef6972b63e7aec)) (by Alexander Neumann)
- dont save computed/temp fields in recipe/compose([`95085fa`](https://github.com/caretech-owl/hive-cli/commit/95085faf0a71c405eb4c8ce131e0983c214c2f94)) (by Alexander Neumann)
- add release script([`89af903`](https://github.com/caretech-owl/hive-cli/commit/89af90331c4be207dfcb9543edf748c91f83095c)) (by Alexander Neumann)
- introduce HIVE_INPUT([`c80c233`](https://github.com/caretech-owl/hive-cli/commit/c80c233e290ff6a1a5f247d58554d6e1f4781cea)) (by Alexander Neumann)

### Bugs fixed:

- try/catch errors when checking container states([`c3a5d35`](https://github.com/caretech-owl/hive-cli/commit/c3a5d35f31e6fe03ccdad95c9353c235b78d13a1)) (by Alexander Neumann)
- consume whole array with [@] in shell script([`8a5f48f`](https://github.com/caretech-owl/hive-cli/commit/8a5f48f356b592e8b4eb36d68f112194ffab88d1)) (by Alexander Neumann)
- update package version([`7ebdcb8`](https://github.com/caretech-owl/hive-cli/commit/7ebdcb8dad945167c28d852294d39a4b2574aea9)) (by Alexander Neumann)

## v0.4.3 (2024-12-12)

### New feature:

- use HIVE_PORT in prod([`a258b12`](https://github.com/caretech-owl/hive-cli/commit/a258b12161593a51ce6e01c8bf0642c5ae3ebc7f)) (by Alexander Neumann)
- add podman/fedora specific args to setup.sh; rename HIVE_CLI_PORT to HIVE_PORT([`2b33dd3`](https://github.com/caretech-owl/hive-cli/commit/2b33dd366a0d4b72edc04188e7db6a7ce87619d6)) (by Alexander Neumann)
- make HIVE_CLI_PORT configurable; default will be 12121([`8879883`](https://github.com/caretech-owl/hive-cli/commit/887988390db6225b32b804ff78cbf6410aa6675b)) (by Alexander Neumann)

### Bugs fixed:

- parse port to int([`2ab6292`](https://github.com/caretech-owl/hive-cli/commit/2ab6292fb1b9524929ccca67909192553ca3c6cf)) (by Alexander Neumann)
- add security-opt to docker run([`f17b117`](https://github.com/caretech-owl/hive-cli/commit/f17b1176b39504a59052413a13172c3a05bee1f9)) (by Alexander Neumann)
- use DOCKER_SOCKET in docker run([`92ee93c`](https://github.com/caretech-owl/hive-cli/commit/92ee93cbe172429c96b874c969db03bdf5cff437)) (by Alexander Neumann)
- update endpoints when recipe changed([`7e3346b`](https://github.com/caretech-owl/hive-cli/commit/7e3346b0ee748b6d17d7275b10e057dc92096ecc)) (by Alexander Neumann)
- escape ret code([`2fe3f7d`](https://github.com/caretech-owl/hive-cli/commit/2fe3f7d23c328036236398f55112e6e5cbb34c72)) (by Alexander Neumann)

## v0.4.2 (2024-12-11)

### New feature:

- make auth location for docker configurable([`7032bf2`](https://github.com/caretech-owl/hive-cli/commit/7032bf204b579b6a51571bf7daa5970c24dfd03d)) (by Alexander Neumann)

### Bugs fixed:

- check path of composer files relative to recipe([`dfec2e3`](https://github.com/caretech-owl/hive-cli/commit/dfec2e3eb14e3115f45c15f36ee35dbb0db5a646)) (by Alexander Neumann)

## v0.4.1 (2024-12-11)

### New feature:

- make recipe and composer files editable([`992a3b3`](https://github.com/caretech-owl/hive-cli/commit/992a3b3e98b349670c404a9f964b693852f01bcb)) (by Alexander Neumann)
- convert hive_id to str since hardware adresses in docker are not unique([`bb449ac`](https://github.com/caretech-owl/hive-cli/commit/bb449ac74980faa57ef91e4c1b6df06fcbe6a3bb)) (by Alexander Neumann)

### Bugs fixed:

- hive_id default was no factory([`8ac2c9e`](https://github.com/caretech-owl/hive-cli/commit/8ac2c9e0c2d98969c9b04194d596bb67a124d039)) (by Alexander Neumann)
- escape ret_code in setup.sh([`ba4711b`](https://github.com/caretech-owl/hive-cli/commit/ba4711b1f1036eb7ab02e650622fd67dd8d98baa)) (by Alexander Neumann)

## v0.4.0 (2024-12-11)

### New feature:

- use return code to determine whether to restart hive-cli([`6d5ffe9`](https://github.com/caretech-owl/hive-cli/commit/6d5ffe933863af7bafe4cd7a2b69ab4124a11849)) (by Alexander Neumann)
- return code 3 when restart is required([`1abd867`](https://github.com/caretech-owl/hive-cli/commit/1abd8678ecc87cb2042f54c9ac9b0eb83095f91f)) (by Alexander Neumann)
- check for cli update when repo update requested([`71987e7`](https://github.com/caretech-owl/hive-cli/commit/71987e7b3c39a1a293df299b819b17d50588b437)) (by Alexander Neumann)
- move HIVE_HOST away from config([`c4a8332`](https://github.com/caretech-owl/hive-cli/commit/c4a83324d4cd0131277b30ca2dc922559c895d03)) (by Alexander Neumann)
- use observer for docker state change in frontend; linting([`dc263dc`](https://github.com/caretech-owl/hive-cli/commit/dc263dcafc6c39c8b001f037886fa1e2e9b6432a)) (by Alexander Neumann)
- add linting([`e80849a`](https://github.com/caretech-owl/hive-cli/commit/e80849a9d9039c8c4e70427d3b01317a3603921d)) (by Alexander Neumann)

### Bugs fixed:

- dont override env when recipe os none([`7da6d35`](https://github.com/caretech-owl/hive-cli/commit/7da6d35ed6d633c5c058c6c95a86b542ab144bbd)) (by Alexander Neumann)
- assume update when local image is not found remotely([`384fdd1`](https://github.com/caretech-owl/hive-cli/commit/384fdd1f13a56edc6522e2a3b7a863b4bd72dac9)) (by Alexander Neumann)
- log formatting([`ed9dd49`](https://github.com/caretech-owl/hive-cli/commit/ed9dd49234bf017aadce3fdb4d793b0c4d8c8629)) (by Alexander Neumann)

## v0.3.1 (2024-12-10)

### New feature:

- link docker host config into container([`9b4ca18`](https://github.com/caretech-owl/hive-cli/commit/9b4ca1827f6ac9523dae679948873b2f82eb12ba)) (by Alexander Neumann)

## v0.3.0 (2024-12-10)

### New feature:

- check for updates([`ee23e79`](https://github.com/caretech-owl/hive-cli/commit/ee23e79f88715a3c5104ae6402276441a7328b24)) (by Alexander Neumann)
- **frontend**: move styling and pass app in INIT([`ea76d30`](https://github.com/caretech-owl/hive-cli/commit/ea76d30c9b76225eb9e5f4b94bf8db612e01ec06)) (by Alexander Neumann)
- **docker**: add update routine([`bfd6dcd`](https://github.com/caretech-owl/hive-cli/commit/bfd6dcdf038867c91d338c0f9361a493f595f920)) (by Alexander Neumann)
- add setup.sh([`dbdd5dc`](https://github.com/caretech-owl/hive-cli/commit/dbdd5dcc83a6a04068a76ce42f61aabeb5e68b1d)) (by Alexander Neumann)

### Bugs fixed:

- **frontend**: show button for correct update state([`d55cda4`](https://github.com/caretech-owl/hive-cli/commit/d55cda4e4257ff2f8c1f9f631ce429342168b46e)) (by Alexander Neumann)

## v0.2.1 (2024-12-05)

### New feature:

- **docker**: add command and entrypoint to recipe([`d223bfc`](https://github.com/caretech-owl/hive-cli/commit/d223bfc0636fc678610c2140db941a134a4ee7e4)) (by Alexander Neumann)
- set favicon and page title([`6750098`](https://github.com/caretech-owl/hive-cli/commit/67500984f179e50880bc34762085123cdc99c0e3)) (by Alexander Neumann)
- add docker compose log([`d9ee959`](https://github.com/caretech-owl/hive-cli/commit/d9ee959a0cfe1b11d5bb7336643892bed21bffc0)) (by Alexander Neumann)

### Bugs fixed:

- **frontend**: capture config for user endpoints([`b22c398`](https://github.com/caretech-owl/hive-cli/commit/b22c3985b7f4430f622dbb1f5510e94cbd4a5906)) (by Alexander Neumann)

## v0.2.0 (2024-12-05)

### New feature:

- add devcareop svg([`a78e46e`](https://github.com/caretech-owl/hive-cli/commit/a78e46e7c74fe1435eab05a0439a1a6a5f216374)) (by Alexander Neumann)
- split state visualization from label([`e19df17`](https://github.com/caretech-owl/hive-cli/commit/e19df171c027626b58eb97e6d960b8d5443119c6)) (by Alexander Neumann)
- set version string from package info([`41d133d`](https://github.com/caretech-owl/hive-cli/commit/41d133d5e3284399aa31f3477205afb27208ded9)) (by Alexander Neumann)
- improve styling([`ce24364`](https://github.com/caretech-owl/hive-cli/commit/ce243642712e41fe41751ced733db8b1d2bb2c9d)) (by Alexander Neumann)
- improve reaction time([`23a4804`](https://github.com/caretech-owl/hive-cli/commit/23a4804971ad2ecf5367a41974a2fde4bff84288)) (by Alexander Neumann)
- add icon to ep definition([`ab725b6`](https://github.com/caretech-owl/hive-cli/commit/ab725b663aeeb7603f625607bfbd72f9fd7de5a4)) (by Alexander Neumann)

### Bugs fixed:

- dev server does not work in script mode([`4bfb542`](https://github.com/caretech-owl/hive-cli/commit/4bfb542bffc795fc7724d03e4c87b4c9d76dcaf2)) (by Alexander Neumann)

## v0.1.4 (2024-12-04)

### Bugs fixed:

- **docker**: docker-compose -> docker compose([`76e1325`](https://github.com/caretech-owl/hive-cli/commit/76e13257cfc15686274ae5887b3a4624136b58bd)) (by Alexander Neumann)

## v0.1.3 (2024-12-04)

### Bugs fixed:

- **docker**: removed printenv([`a8cff51`](https://github.com/caretech-owl/hive-cli/commit/a8cff51f2ce867df0fbfcee9fb58c796ff83c91f)) (by Alexander Neumann)

## v0.1.2 (2024-12-04)

### New feature:

- add poe([`fa07d83`](https://github.com/caretech-owl/hive-cli/commit/fa07d8378386d4520725c3425e3beda012a89a31)) (by Alexander Neumann)
- improve style of endpoints([`f117c79`](https://github.com/caretech-owl/hive-cli/commit/f117c79339425e1b1b3fa74a628a9b342d638bff)) (by Alexander Neumann)
- add drawio concept sketch([`ac4b1c1`](https://github.com/caretech-owl/hive-cli/commit/ac4b1c1fc994762566a02c4eb0b3c0628107e0e4)) (by Alexander Neumann)
- initial commit([`7d11523`](https://github.com/caretech-owl/hive-cli/commit/7d115235118be9a06dbd3018825449bd7753644f)) (by Alexander Neumann)

### Bugs fixed:

- add environment vars to check_container as well([`1cbf098`](https://github.com/caretech-owl/hive-cli/commit/1cbf098349a1b8fb33b6085cbc2467e5e91885ef)) (by Alexander Neumann)
- unify config([`03dd405`](https://github.com/caretech-owl/hive-cli/commit/03dd4054ca10b7500b19453b6d22aa74f9611939)) (by Alexander Neumann)