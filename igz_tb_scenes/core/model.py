# =========================================================================
# Pasta: igz_tb_scenes/core/
# Arquivo: model.py
# Descrição: Estrutura de dados da Cena e timeline da sequência.
# =========================================================================
from .math_utils import _interpolar

_EPS = 1e-8

class Scene:
    def __init__(self, nome, eye, target, fov, hold_s=1.0, transicao_s=2.0):
        self.nome = str(nome)
        self.eye = [float(eye[0]), float(eye[1]), float(eye[2])]
        self.target = [float(target[0]), float(target[1]), float(target[2])]
        self.fov = float(fov)
        self.hold_s = float(hold_s)
        self.transicao_s = float(transicao_s)

    def to_dict(self):
        return {"nome": self.nome, "eye": list(self.eye), "target": list(self.target), "fov": self.fov, "hold_s": self.hold_s, "transicao_s": self.transicao_s}

    @classmethod
    def from_dict(cls, d):
        return cls(d.get("nome", "Scene"), d.get("eye", [0.0, -10.0, 5.0]), d.get("target", [0.0, 0.0, 0.0]), d.get("fov", 30.0), d.get("hold_s", 1.0), d.get("transicao_s", 2.0))

def sequence_duration(cenas) -> float:
    n = len(cenas)
    if n == 0: return 0.0
    if n == 1: return max(float(cenas[0].hold_s), 0.0)
    total = 0.0
    for i in range(n):
        total += max(float(cenas[i].hold_s), 0.0)
        if i < n - 1: total += max(float(cenas[i].transicao_s), 0.0)
    return total

def sample_sequence(cenas, t, suavizacao="Smooth"):
    n = len(cenas)
    if n == 0: return [0.0, -10.0, 5.0], [0.0, 0.0, 0.0], 30.0
    if n == 1 or t <= 0.0:
        s = cenas[0]
        return list(s.eye), list(s.target), s.fov
    acc = 0.0
    for i in range(n):
        s = cenas[i]
        if t < acc + s.hold_s: return list(s.eye), list(s.target), s.fov
        acc += s.hold_s
        if i >= n - 1: break
        trans = s.transicao_s if s.transicao_s > _EPS else _EPS
        if t < acc + trans:
            u = (t - acc) / trans
            return _interpolar(cenas, i, u, suavizacao)
        acc += trans
    s = cenas[-1]
    return list(s.eye), list(s.target), s.fov