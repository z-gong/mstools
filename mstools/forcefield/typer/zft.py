from .typer import *
from ..errors import *

try:
    import openbabel as ob
    import pybel
except:
    OPENBABEL_IMPORTED = True
else:
    OPENBABEL_IMPORTED = True


class TypeDefine():
    def __init__(self, name, smarts, charge):
        self.name = name
        self.obsmarts = None
        self.charge = charge
        if smarts is not None:
            self.obsmarts = ob.OBSmartsPattern()
            if not self.obsmarts.Init(smarts):
                raise Exception('Invalid SMARTS: %s' % smarts)

        self.children: [TypeDefine] = []
        self.parent: TypeDefine = None

    def __repr__(self):
        return '<TypeDefine: %s>' % self.name

    def add_child(self, define):
        if define not in self.children:
            self.children.append(define)
            define.parent = self


class ZftTyper(Typer):
    '''
    ZftTyper type a topology or molecule with local environment defined by SMARTS.
    A hierarchical strategy is used to make the atom type definition extendable.
    '''
    def __init__(self, file):
        super().__init__()
        self.defines: {str: TypeDefine} = {}
        self.define_root = TypeDefine('UNDEFINED', None, 0)
        self._file = file
        self._parse(file)

    def __repr__(self):
        return '<ZftTyper: %s>' % self._file

    def _parse(self, file):
        if not OPENBABEL_IMPORTED:
            raise Exception('Cannot import openbabel')

        with open(file)  as f:
            lines = f.read().splitlines()

        section = ''
        tree_lines = []
        for line in lines:
            line = line.split('##')[0]
            if line.strip() == '':
                continue
            if line.strip() == 'TypeDefinition':
                section = 'TypeDefinition'
                continue
            if line.strip() == 'HierarchicalTree':
                section = 'HierarchicalTree'
                continue
            if section == 'TypeDefinition':
                try:
                    name, smarts, charge = line.strip().split()
                except:
                    raise Exception('smarts and charge should be provided: %s' % line)
                self.defines[name] = TypeDefine(name, smarts, charge)
            if section == 'HierarchicalTree':
                tree_lines.append(line.rstrip())

        last_level = 0
        last_define = self.define_root
        for line in tree_lines:
            name = line.lstrip()
            indent = len(line) - len(name)
            if indent % 4 != 0:
                raise Exception('Indentation for HierarchicalTree should be 4 spaces: %s' % line)
            level = (indent) // 4 + 1
            if level == last_level + 1:
                parent = last_define
            elif level <= last_level:
                parent = last_define
                for i in range(last_level - level + 1):
                    parent = parent.parent
            else:
                raise Exception('Invalid indentation: %s' % line)
            last_level = level
            try:
                last_define = self.defines[name]
            except:
                raise Exception('Atom type not found in TypeDefinition section: %s' % line)
            parent.add_child(last_define)

    def type_molecule(self, molecule):
        '''
        Type molecule with predefined SMARTS information

        Parameters
        ----------
        molecule : Molecule

        Returns
        -------

        '''
        obmol = molecule._obmol
        if obmol is None:
            raise TypingNotSupportedError('obmol attribute not found for %s' % str(molecule))

        possible_defines = {i: [] for i in range(molecule.n_atom)}
        for define in self.defines.values():
            obsmarts = define.obsmarts
            obsmarts.Match(obmol)
            results = list(obsmarts.GetMapList())
            for indexes in results:
                idx = indexes[0] - 1
                possible_defines[idx].append(define)

        _undefined = []
        for i, atom in enumerate(molecule.atoms):
            define = self._get_deepest_define(possible_defines[i], self.define_root)
            if define is self.define_root:
                _undefined.append(atom.name)
            else:
                atom.type = define.name
        if _undefined != []:
            raise TypingUndefinedError('Definition not found for %i atoms: %s' % (
                len(_undefined), ' '.join(_undefined)))

    def _get_deepest_define(self, defines, parent: TypeDefine):
        for define in parent.children:
            if define in defines:
                return self._get_deepest_define(defines, define)
        return parent
