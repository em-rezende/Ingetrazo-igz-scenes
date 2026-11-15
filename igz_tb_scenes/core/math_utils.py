# =========================================================================
# Pasta: igz_tb_scenes/core/
# Arquivo: math_utils.py
# Descrição: Matemática de interpolação suave (interpolação de câmera).
# =========================================================================
from PySide6.QtGui import QVector3D

def _smoothstep(u: float) -> float:
    u = max(0.0, min(1.0, u))
    return u * u * (3.0 - 2.0 * u)

def _catmull_rom(p0, p1, p2, p3, t):
    t2 = t * t
    t3 = t2 * t
    def comp(a, b, c, d):
        return 0.5 * ((2.0 * b) + (-a + c) * t + (2.0 * a - 5.0 * b + 4.0 * c - d) * t2 + (-a + 3.0 * b - 3.0 * c + d) * t3)
    return QVector3D(
        comp(p0.x(), p1.x(), p2.x(), p3.x()), 
        comp(p0.y(), p1.y(), p2.y(), p3.y()), 
        comp(p0.z(), p1.z(), p2.z(), p3.z())
    )

def _interpolar(cenas, i, u, suavizacao):
    n = len(cenas)
    a = cenas[i]
    b = cenas[min(i + 1, n - 1)]
    u = max(0.0, min(1.0, u))
    e = u if suavizacao == "Linear" else _smoothstep(u)
    if suavizacao == "Catmull-Rom" and n >= 3:
        p_prev = cenas[i - 1] if i > 0 else a
        p_next = cenas[i + 2] if (i + 2) <= n - 1 else b
        ev = _catmull_rom(QVector3D(*p_prev.eye), QVector3D(*a.eye), QVector3D(*b.eye), QVector3D(*p_next.eye), e)
        tv = _catmull_rom(QVector3D(*p_prev.target), QVector3D(*a.target), QVector3D(*b.target), QVector3D(*p_next.target), e)
        eye = [ev.x(), ev.y(), ev.z()]
        tgt = [tv.x(), tv.y(), tv.z()]
    else:
        eye = [a.eye[k] + (b.eye[k] - a.eye[k]) * e for k in range(3)]
        tgt = [a.target[k] + (b.target[k] - a.target[k]) * e for k in range(3)]
    fov = a.fov + (b.fov - a.fov) * e
    return eye, tgt, fov