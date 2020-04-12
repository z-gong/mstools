#!/usr/bin/env python3

from mstools.forcefield import FFToolParameterSet

import os

cwd = os.path.dirname(os.path.abspath(__file__))
params = FFToolParameterSet(cwd + '/files/oplsaa.ff')

def test_fftool():
    br = params.atom_types['Br']
    assert br.mass == 79.904
    assert br.charge == -1.0
    assert br.epsilon == 0.37656
    assert br.sigma == 4.624 / 10

    bond = params.bond_terms['CT,CT']
    assert bond.length == 1.529 / 10
    assert bond.k == 2242.6 / 2

    angle = params.angle_terms['CT,CT,HC']
    assert angle.theta == 110.7
    assert angle.k == 313.8 / 2

    dihedral = params.dihedral_terms['CT,CT,CT,HC']
    assert dihedral.k1 == 0
    assert dihedral.k2 == 0
    assert dihedral.k3 == 1.2552 / 2
    assert dihedral.k4 == 0

    dihedral = params.dihedral_terms['CT,CT,CT,CT']
    assert dihedral.k1 == 5.4392 / 2
    assert dihedral.k2 == -0.2092 / 2
    assert dihedral.k3 == 0.8368 / 2
    assert dihedral.k4 == 0

    improper = params.improper_terms['N,C,CT,CT']
    assert improper.k == 8.368 / 2
