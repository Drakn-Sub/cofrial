# Uso: python cuentas/demo/generar_camion3d.py  (requiere trimesh; solo para regenerar el modelo)
"""Modelo 3D simple de camión refrigerado (glTF binario) para el mapa de la torre de control.
Ejes glTF: X = largo (cabina hacia +X), Y = alto, Z = ancho. Medidas en metros."""
import numpy as np, trimesh
from trimesh.visual.material import PBRMaterial

def pieza(malla, rgba, metal=0.1, rugosidad=0.6):
    malla.visual = trimesh.visual.TextureVisuals(material=PBRMaterial(baseColorFactor=rgba, metallicFactor=metal, roughnessFactor=rugosidad))
    return malla

def caja(lx, ly, lz, cx, cy, cz):
    m = trimesh.creation.box(extents=(lx, ly, lz)); m.apply_translation((cx, cy, cz)); return m

escena = trimesh.Scene()
blanco = [235, 240, 243, 255]; cabina = [40, 52, 60, 255]; vidrio = [120, 160, 185, 255]; goma = [25, 25, 25, 255]
escena.add_geometry(pieza(caja(8.2, 2.7, 2.5, -1.4, 2.35, 0), blanco), node_name="caja_frigorifica")
escena.add_geometry(pieza(caja(0.5, 0.9, 1.6, -5.65, 3.0, 0), [190, 198, 204, 255]), node_name="equipo_frio")
escena.add_geometry(pieza(caja(2.3, 2.3, 2.45, 4.0, 2.05, 0), cabina, 0.3, 0.4), node_name="cabina")
escena.add_geometry(pieza(caja(0.08, 0.9, 2.1, 5.16, 2.55, 0), vidrio, 0.0, 0.1), node_name="parabrisas")
escena.add_geometry(pieza(caja(11.0, 0.35, 2.2, -0.3, 0.85, 0), [60, 66, 70, 255]), node_name="chasis")
for x in (4.0, -2.2, -3.7):
    for z in (-1.05, 1.05):
        r = trimesh.creation.cylinder(radius=0.55, height=0.4, sections=20)
        r.apply_translation((x, 0.55, z)); escena.add_geometry(pieza(r, goma, 0.0, 0.9))
import pathlib
destino = str(pathlib.Path(__file__).resolve().parents[1] / "static" / "cofrial" / "mapa" / "camion.glb")
escena.export(destino); print(destino, len(open(destino, "rb").read()), "bytes")
