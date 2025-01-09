from pathlib import Path

HEADER_STYLE = "text-lg"
WARNING_STYLE = (
    "bg-rose-500 text-white py-2 px-4 rounded-lg text-center text-lg font-bold"
)
INFO_STYLE = (
    "bg-green-500 text-white py-2 px-4 rounded-lg text-center text-lg font-bold"
)
SIMPLE_STYLE = "py-2 px-4 rounded-lg text-center text-lg font-bold"
LOG_STYLE = "font: 12px/1.5 monospace; white-space: pre-wrap; background-color: #f7f7f7; border-radius: 5px; border: 1px solid #ddd;"
SERVICE_ACTIVE_STYLE = (
    "bg-green-500 text-white py-2 px-4 rounded-lg text-center text-lg font-bold h-40"
)
DEACTIVATED_STYLE = (
    "bg-gray-500 text-white py-2 px-4 rounded-lg text-center text-lg font-bold"
)
PENDING_STYLE = (
    "bg-yellow-500 text-white py-2 px-4 rounded-lg text-center text-lg font-bold"
)
UPDATE_STYLE = (
    "bg-purple-500 text-white py-2 px-4 rounded-lg text-center text-lg font-bold"
)
TEXT_INFO_STYLE = "text-sm text-gray-500"

ICO = """
<svg width="100%" height="100%" viewBox="0 0 320 320" version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" xml:space="preserve" xmlns:serif="http://www.serif.com/" style="fill-rule:evenodd;clip-rule:evenodd;stroke-linejoin:round;stroke-miterlimit:2;">
    <g transform="matrix(0.120848,0.120848,-0.120848,0.120848,85.2165,-21.2722)">
        <path d="M984.281,365.458L983.823,101.308C983.823,101.264 983.823,101.221 983.823,101.177C983.823,-128.021 1169.62,-313.823 1398.82,-313.823C1627.87,-313.823 1813.82,-127.867 1813.82,101.177C1813.82,330.376 1628.02,516.177 1398.82,516.177C1398.78,516.177 1398.74,516.177 1398.69,516.177L1134.54,515.719L1135,779.87C1135,779.913 1135,779.957 1135,780C1135,1009.2 949.198,1195 720,1195C490.955,1195 305,1009.05 305,780C305,550.802 490.802,365 720,365C720.043,365 720.087,365 720.13,365C720.13,365 843.054,365.213 984.281,365.458ZM984.541,515.459L719.947,515L719.903,515C573.592,515.052 455,633.677 455,780C455,926.257 573.743,1045 720,1045C866.338,1045 984.971,926.384 985,780.053L984.541,515.459ZM1134.28,365.718C1275.7,365.964 1398.9,366.177 1398.92,366.177C1545.23,366.125 1663.82,247.501 1663.82,101.177C1663.82,-45.08 1545.08,-163.823 1398.82,-163.823C1252.49,-163.823 1133.85,-45.207 1133.82,101.125L1134.28,365.718Z" style="fill:url(#_Linear1);"/>
    </g>
    <defs>
        <linearGradient id="_Linear1" x1="0" y1="0" x2="1" y2="0" gradientUnits="userSpaceOnUse" gradientTransform="matrix(1508.82,0,0,1508.82,305,440.589)"><stop offset="0" style="stop-color:rgb(19,170,202);stop-opacity:1"/><stop offset="0.5" style="stop-color:rgb(245,135,36);stop-opacity:1"/><stop offset="1" style="stop-color:rgb(251,196,15);stop-opacity:1"/></linearGradient>
    </defs>
</svg>
"""


def list_files(startpath: Path) -> list[tuple[int, str]]:
    out = []
    for root, _, files in startpath.walk():
        if any(p.startswith(".git") or p.startswith("__") for p in root.parts):
            continue
        level = root.relative_to(startpath).parts.__len__()
        out.append((level, root.name))
        out.extend([(level + 1, f) for f in files])
    return out
