"""Genera las fotos de producto de la tienda de demostración (una vez, fuera de producción).

    python cuentas/demo/generar_imagenes.py <carpeta con los SVG de @twemoji/svg>

Íconos: Twemoji (c) Twitter/X y colaboradores, licencia CC-BY 4.0.
"""
import pathlib
import sys

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from catalogo import PRODUCTOS  # noqa: E402

DESTINO = pathlib.Path(__file__).parent / "imagenes"
ESTILO = {
    "Congelados": ("#eaf4fc", "#bcdcf4", "#1f5f8b", "−18 °C"),
    "Refrigerados": ("#eef8f1", "#c3e8d0", "#24724a", "0 a 4 °C"),
}
PLANTILLA = """<!doctype html><html><body style="margin:0">
<div style="width:800px;height:800px;position:relative;overflow:hidden;font-family:'DejaVu Sans',sans-serif;
            background:radial-gradient(circle at 50% 42%, {c1} 0%, {c2} 100%)">
  <div style="position:absolute;inset:0;opacity:.18;background-image:
       radial-gradient(circle at 15% 20%, #fff 0 3px, transparent 4px),
       radial-gradient(circle at 80% 15%, #fff 0 5px, transparent 6px),
       radial-gradient(circle at 88% 70%, #fff 0 4px, transparent 5px),
       radial-gradient(circle at 10% 82%, #fff 0 6px, transparent 7px)"></div>
  <div style="position:absolute;left:50%;top:50%;width:470px;height:470px;transform:translate(-50%,-54%);
              filter:drop-shadow(0 28px 30px rgba(0,0,0,.22))">{svg}</div>
  <div style="position:absolute;left:36px;top:34px;padding:10px 18px;border-radius:999px;background:#fff;
              color:{tinta};font-size:26px;font-weight:bold;box-shadow:0 4px 14px rgba(0,0,0,.08)">❄ {temp}</div>
  <div style="position:absolute;left:0;right:0;bottom:40px;text-align:center;color:{tinta};
              font-size:30px;letter-spacing:6px;font-weight:bold;opacity:.75">COFRIAL</div>
</div></body></html>"""


def main(carpeta_svg):
    DESTINO.mkdir(exist_ok=True)
    with sync_playwright() as p:
        navegador = p.chromium.launch()
        pagina = navegador.new_page(viewport={"width": 800, "height": 800})
        for nombre, categoria, *_, archivo, icono, _desc in PRODUCTOS:
            c1, c2, tinta, temp = ESTILO[categoria]
            svg = (pathlib.Path(carpeta_svg) / f"{icono}.svg").read_text()
            svg = svg.replace("<svg ", '<svg width="470" height="470" ', 1)
            pagina.set_content(PLANTILLA.format(c1=c1, c2=c2, tinta=tinta, temp=temp, svg=svg))
            pagina.screenshot(path=str(DESTINO / f"{archivo}.jpg"), type="jpeg", quality=85)
            print("ok", archivo)
        navegador.close()


if __name__ == "__main__":
    main(sys.argv[1])
