#!/usr/bin/env python3

from mstools.wrapper import DFF
from mstools.forcefield import DffTyper
from mstools.topology import Topology, Molecule

import os

cwd = os.path.dirname(os.path.abspath(__file__))


def test_typing():
    im2eben = Molecule.from_smiles('C[n+]1cn(cc1)CCc1ccccc1')
    fsi = Molecule.from_smiles('FS(=O)(=O)[N-]S(=O)(=O)F')
    top = Topology([im2eben, fsi])

    dff = DFF(r'D:\Projects\DFF\Developing')
    typer = DffTyper(dff, r'D:\Projects\DFF\Developing\database\TEAMFF.ref\IL\IL.ext')
    typer.type(top)

    assert [atom.type for atom in im2eben.atoms] == (
            ['c_4nph3', 'n_35+da', 'c_35an2', 'n_35+da', 'c_35an', 'c_35an', 'c_4np',
             'c_4h2', 'c_3ac', 'c_3a', 'c_3a', 'c_3a', 'c_3a', 'c_3a']
            + ['h_1'] * 15)
    assert [atom.type for atom in fsi.atoms] == (
        ['f_1', 's_4o', 'o_1', 'o_1', 'n_2-', 's_4o', 'o_1', 'o_1', 'f_1'])
