from collections import namedtuple
import math
from distutils.util import strtobool
from .errors import *
from ..constant import *


class FFTermFactory():
    '''
    Factory class for force field terms.

    Mainly used for loading a FFTerm from xml element stored in ZFP file.
    '''

    _class_map = {}

    @staticmethod
    def register(klass):
        '''
        Register a force field term so that it can be read from or write into a ZFP file.

        Parameters
        ----------
        klass : subclass of FFTerm
        '''
        FFTermFactory._class_map[klass.__name__] = klass

    @staticmethod
    def create_from_zfp(name, d):
        '''
        Reconstruct a FFTerm using a dict of attributes read from ZFP xml file.

        Essentially it finds the class for the term, and calls the constructor of the class.
        Every class to be reconstructed should have a class attribute `_zfp_attrs`.
        This dict records which attributes should be saved into ZFP xml file,
        and it is also used as the arguments for initializing a FFTerm.
        It also tell the data type of these attributes.

        Some force field terms can not be fully built from the constructor.
        Then :func:`FFTerm._from_zfp_extra` should be implemented for those terms,
        and it will be called to do some extra works.

        Parameters
        ----------
        name : str
            Class name of the term to be constructed
        d : dict, [str, str]
            Attributes loaded from ZFP xml element

        Returns
        -------
        term : subclass of FFTerm

        '''
        # must use kwargs instead of args to init the cls,
        # in case there is mistake in the sequence of init arguments
        try:
            cls = FFTermFactory._class_map[name]
        except:
            raise Exception('Invalid force field term: %s' % name)
        kwargs = {}
        for attr, func in cls._zfp_attrs.items():
            kwargs[attr] = func(d[attr])
        try:
            term = cls(**kwargs)
        except:
            raise Exception('Cannot init %s with kwargs %s' % (name, str(d)))
        term._from_zfp_extra(d)
        return term


class FFTerm():
    '''
    Base class for all force field terms like :class:`AtomType`, :class:`BondTerm`, etc...

    Attributes
    ----------
    version : str
        Version is used mainly in :class:`PPF` format by DFF.
    comments : list of str
        Comments is useful for debugging when generating input files for simulation engines.
    '''

    _zfp_attrs = {}
    '''
    The attributes that will be saved into or loaded from ZFP file.
    This dict must be overridden by every subclasses that can be saved into or reconstructed from ZFP xml file.
    '''

    def __init__(self):
        self.version = None
        self.comments: [str] = []

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.name)

    @property
    def name(self):
        '''
        The name of this force field term.

        Returns
        -------
        name : str
        '''
        raise NotImplementedError('This property should be implemented by subclasses')

    def to_zfp(self):
        '''
        Pack the attributes of a term into a dict so that can be saved into ZFP xml file.

        Every class to be packed should have a class property `zfp_attrs`.
        This dict records which attributes should be saved into ZFP xml file,
        and it is also used as the arguments for initializing a FFTerm.
        It also tell the data type of these attributes.

        Returns
        -------
        d : dict, [str, str]
        '''
        d = {}
        for attr, func in self._zfp_attrs.items():
            d[attr] = str(getattr(self, attr))
        d.update(self._to_zfp_extra())
        return d

    def _to_zfp_extra(self):
        '''
        Pack extra information for some special terms.

        e.g. PeriodicDihedralTerm can contain arbitrary numbers of dihedral parameters.

        Returns
        -------
        d : dict, [str, str]
        '''
        return {}

    def _from_zfp_extra(self, d):
        '''
        Some force field terms can not be fully built from the constructor.
        This function is called by :func:`FFTermFactory.create_from_zfp` to do some extra works.

        e.g. PeriodicDihedralTerm need to rebuild its own storage of multiple dihedral parameters

        Parameters
        ----------
        d : dict, [str, str]
        '''
        pass

    def evaluate_energy(self, val):
        '''
        Evaluate the energy for a force field term like HarmonicBondTerm, PeriodicDihedralTerm, etc...

        It is mainly for debugging. It is not (and can not be) implemented for all terms.

        Parameters
        ----------
        val : float
            The value of distance, angle, dihedral or improper.

        Returns
        -------
        energy : float
        '''
        raise NotImplementedError('This method is invalid for this term')


class AtomType(FFTerm):
    '''
    AtomType is the most fundamental element in a force field.
    It determines which :class:`VdwTerm`, :class:`BondTerm`, etc...
    will be used to describe the energy functions between a specific set of atoms.

    Equivalent table (EQT) is extensively used in mstools.
    It helps decreasing the number of force field terms significantly without losing generality and accuracy,
    thus making the force field extendable.

    Parameters
    ----------
    name : str
        The name of this atom type.
    mass : float , optional
        The mass of this atom type.
    charge : float , optional
        The charge of this atom type.
    eqt_vdw : str , optional
        The equivalent type for vdW parameters
    eqt_q_inc : str , optional
        The equivalent type for bond charge increment parameters
    eqt_bond : str , optional
        The equivalent type for bond parameters
    eqt_ang_c : str , optional
        The equivalent type for angle parameters if this atom type is the center of an angle
    eqt_ang_s: str , optional
        The equivalent type for angle parameters if this atom type is the side of an angle
    eqt_dih_c : str , optional
        The equivalent type for dihedral parameters if this atom type is the center of a dihedral
    eqt_dih_s: str , optional
        The equivalent type for dihedral parameters if this atom type is the side of a dihedral
    eqt_imp_c : str , optional
        The equivalent type for improper parameters if this atom type is the center of an improper
    eqt_imp_s : str , optional
        The equivalent type for improper parameters if this atom type is the side of an improper
    eqt_polar : str , optional
        The equivalent type for polarization parameters

    Attributes
    ----------
    mass : float
        The mass of this atom type. -1 means not provided in the force field.
        Mass is not mandatory, because finally we are going to take the masses from the :class:`~mstools.topology.Topology`.
        However, masses in force field can be used to assign the masses in topology.
    charge : float
        The charge of this atom type.
        Similar to mass, the charges we are finally going to use are from the :class:`~mstools.topology.Topology`.
        But charges in force field can be used to assign the charges in topology.
    eqt_vdw : str
        The equivalent type for vdW parameters
    eqt_q_inc : str
        The equivalent type for bond charge increment parameters
    eqt_bond : str
        The equivalent type for bond parameters
    eqt_ang_c : str
        The equivalent type for angle parameters if this atom type is the center of an angle
    eqt_ang_s: str
        The equivalent type for angle parameters if this atom type is the side of an angle
    eqt_dih_c : str
        The equivalent type for dihedral parameters if this atom type is the center of a dihedral
    eqt_dih_s: str
        The equivalent type for dihedral parameters if this atom type is the side of a dihedral
    eqt_imp_c : str
        The equivalent type for improper parameters if this atom type is the center of an improper
    eqt_imp_s : str
        The equivalent type for improper parameters if this atom type is the side of an improper
    eqt_polar : str
        The equivalent type for polarization parameters
    '''
    _zfp_attrs = {
        'name'     : str,
        'mass'     : float,
        'charge'   : float,
        'eqt_vdw'  : str,
        'eqt_bond' : str,
        'eqt_q_inc': str,
        'eqt_ang_c': str,
        'eqt_ang_s': str,
        'eqt_dih_c': str,
        'eqt_dih_s': str,
        'eqt_imp_c': str,
        'eqt_imp_s': str,
        'eqt_polar': str,
    }

    def __init__(self, name, mass=-1, charge=0,
                 eqt_vdw=None, eqt_q_inc=None, eqt_bond=None,
                 eqt_ang_c=None, eqt_ang_s=None, eqt_dih_c=None, eqt_dih_s=None,
                 eqt_imp_c=None, eqt_imp_s=None, eqt_polar=None):
        super().__init__()
        self._name = name
        # mass is only used for assign mass of topology in case mass not exist in topology
        # mass = -1 means unknown
        self.mass = mass
        self.charge = charge
        self.eqt_vdw = eqt_vdw or name
        self.eqt_q_inc = eqt_q_inc or name
        self.eqt_bond = eqt_bond or name
        self.eqt_ang_c = eqt_ang_c or name
        self.eqt_ang_s = eqt_ang_s or name
        self.eqt_dih_c = eqt_dih_c or name
        self.eqt_dih_s = eqt_dih_s or name
        self.eqt_imp_c = eqt_imp_c or name
        self.eqt_imp_s = eqt_imp_s or name
        self.eqt_polar = eqt_polar or name

    @property
    def name(self):
        '''
        The name of this atom type.

        :setter: Set the name of this atom type

        Returns
        -------
        name : str
        '''
        return self._name

    @name.setter
    def name(self, value):
        # this is a trick allowing from_zfp() to work correctly
        self._name = value

    def __lt__(self, other):
        return self.name < other.name

    def __gt__(self, other):
        return self.name > other.name


FFTermFactory.register(AtomType)


class ChargeIncrementTerm(FFTerm):
    '''
    ChargeIncrementTerm describes the offset of charge between two atom types when they are bonded.

    Two atom types and the offset from the second to first should be provided to construct this term.
    e.g. The following example means when h_1 and c_4 are bonded,
    0.06 element charges will be transferred from c_4 to h_1.

    >>> term = ChargeIncrementTerm('h_1', 'c_4', 0.06)

    During the initialization, the two atom types will be sorted by their string.
    The value will be modified to represent the offset from the second to the first atom types after sorting.

    >>> print(term.type1, term.type2, term.value)
        c_4 h_1 -0.06

    Parameters
    ----------
    type1 : str
        The string of first atom type
    type2 : str
        The string of second atom type
    value : float
        The offset from type2 to type1

    Attributes
    ----------
    type1 : str
        The string of first atom type
    type2 : str
        The string of second atom type
    value : float
        The offset from type2 to type1
    '''
    _zfp_attrs = {
        'type1': str,
        'type2': str,
        'value': float,
    }

    def __init__(self, type1, type2, value):
        super().__init__()
        if type1 == type2 and value != 0:
            raise ChargeIncrementNonZeroError('Non-zero charge increment between atoms of same type')

        at1, at2 = sorted([type1, type2])
        self.type1 = at1
        self.type2 = at2
        self.value = value if at1 == type1 else -value

    @property
    def name(self):
        return '%s,%s' % (self.type1, self.type2)

    def __lt__(self, other):
        return [self.type1, self.type2] < [other.type1, other.type2]

    def __gt__(self, other):
        return [self.type1, self.type2] > [other.type1, other.type2]


FFTermFactory.register(ChargeIncrementTerm)


class VdwTerm(FFTerm):
    '''
    Base class for all vdW terms.

    Subclasses should be implemented for each functional form,
    e.g. :class:`LJ126Term`, :class:`MieTerm`.

    During the initialization, the two atom types will be sorted by their string.

    Parameters
    ----------
    type1 : str
    type2 : str

    Attributes
    ----------
    type1 : str
    type2 : str
    '''

    def __init__(self, type1, type2):
        super().__init__()
        at1, at2 = sorted([type1, type2])
        self.type1 = at1
        self.type2 = at2

    @property
    def name(self):
        return '%s,%s' % (self.type1, self.type2)

    def __lt__(self, other):
        return [self.type1, self.type2] < [other.type1, other.type2]

    def __gt__(self, other):
        return [self.type1, self.type2] > [other.type1, other.type2]


class BondTerm(FFTerm):
    '''
    Base class for all bond terms.

    Subclasses should be implemented for each functional form,
    e.g. :class:`HarmonicBondTerm`.

    During the initialization, the two atom types will be sorted by their string.

    Parameters
    ----------
    type1 : str
    type2 : str
    length : float
    fixed : bool

    Attributes
    ----------
    type1 : str
    type2 : str
    length : float
    fixed : bool
    '''

    def __init__(self, type1, type2, length, fixed=False):
        super().__init__()
        at1, at2 = sorted([type1, type2])
        self.type1 = at1
        self.type2 = at2
        self.length = length
        self.fixed = fixed

    @property
    def name(self):
        return '%s,%s' % (self.type1, self.type2)

    def __lt__(self, other):
        return [self.type1, self.type2] < [other.type1, other.type2]

    def __gt__(self, other):
        return [self.type1, self.type2] > [other.type1, other.type2]


class AngleTerm(FFTerm):
    '''
    Base class for all angle terms.

    Subclasses should be implemented for each functional form,
    e.g. :class:`HarmonicAngleTerm`, :class:`SDKAngleTerm`.

    During the initialization, the two side atom types will be sorted by their string.

    Parameters
    ----------
    type1 : str
    type2 : str
    type3 : str
    theta : float
    fixed : bool

    Attributes
    ----------
    type1 : str
    type2 : str
    type3 : str
    theta : float
    fixed : bool
    '''

    def __init__(self, type1, type2, type3, theta, fixed=False):
        super().__init__()
        at1, at3 = sorted([type1, type3])
        self.type1 = at1
        self.type2 = type2
        self.type3 = at3
        self.theta = theta
        self.fixed = fixed

    @property
    def name(self):
        return '%s,%s,%s' % (self.type1, self.type2, self.type3)

    def __lt__(self, other):
        return [self.type1, self.type2, self.type3] < [other.type1, other.type2, other.type3]

    def __gt__(self, other):
        return [self.type1, self.type2, self.type3] > [other.type1, other.type2, other.type3]


class DihedralTerm(FFTerm):
    '''
    Base class for all dihedral terms.

    Subclasses should be implemented for each functional form,
    e.g. :class:`PeriodicDihedralTerm`.

    During the initialization, the sequence of atom types to use `i-j-k-l` or `l-k-j-i`
    will be determined by their string order.

    DihedralTerm allows wildcard(*) for side atoms.
    For sorting purpose, the wildcard will always be the last.
    During force field matching, the terms with wildcard will have lower priority.
    The terms with wildcard will be used only if exact match cannot be found.

    Parameters
    ----------
    type1 : str
    type2 : str
    type3 : str
    type4 : str

    Attributes
    ----------
    type1 : str
    type2 : str
    type3 : str
    type4 : str
    '''

    def __init__(self, type1, type2, type3, type4):
        super().__init__()
        if '*' in [type2, type3]:
            raise Exception('Wildcard not allowed for center atoms in DihedralTerm')
        if [type1, type4].count('*') in [0, 2]:
            at1, at2, at3, at4 = min([(type1, type2, type3, type4), (type4, type3, type2, type1)])
        elif type1 == '*':
            at1, at2, at3, at4 = (type4, type3, type2, type1)
        else:
            at1, at2, at3, at4 = (type1, type2, type3, type4)
        self.type1 = at1
        self.type2 = at2
        self.type3 = at3
        self.type4 = at4

    @property
    def name(self):
        return '%s,%s,%s,%s' % (self.type1, self.type2, self.type3, self.type4)

    def __lt__(self, other):
        return [self.type1, self.type2, self.type3, self.type4] \
               < [other.type1, other.type2, other.type3, other.type4]

    def __gt__(self, other):
        return [self.type1, self.type2, self.type3, self.type4] \
               > [other.type1, other.type2, other.type3, other.type4]

    @property
    def is_zero(self):
        '''
        Whether or not this dihedral terms always give zero energy.

        For linear groups like alkyne and nitrile, dihedral terms are presented in topology.
        But the parameters for these terms usually equal to zero.

        Returns
        -------
        is :  bool
        '''
        return False


class ImproperTerm(FFTerm):
    '''
    Base class for all improper terms.

    Subclasses should be implemented for each functional form,
    e.g. :class:`PeriodicImproperTerm`.

    During the initialization, the three side atom types will be sorted by their string.

    Improper term is usually used to keep 3-coordinated structures in the same plane.
    The first atom is the central atom, following the convention of GROMACS and CHARMM.
    However, the definition of the value of improper i-j-k-l is vague.
    CHARMM defines the value of the improper as the angle between plane i-j-k and j-k-l.
    Whereas OPLS defines the value as the angle between j-k-i and k-i-l.

    ImproperTerm allows wildcard(*) for side atoms.
    During force field matching, the terms with wildcard will have lower priority.
    The terms with wildcard will be used only if exact match cannot be found.

    Parameters
    ----------
    type1 : str
    type2 : str
    type3 : str
    type4 : str

    Attributes
    ----------
    type1 : str
    type2 : str
    type3 : str
    type4 : str
    '''

    def __init__(self, type1, type2, type3, type4):
        super().__init__()
        if type1 == '*':
            raise Exception('Wildcard not allowed for center atoms in ImproperTerm')
        non_wildcard = [t for t in (type2, type3, type4) if t != '*']
        at2, at3, at4 = list(sorted(non_wildcard)) + ['*'] * (3 - len(non_wildcard))
        self.type1 = type1
        self.type2 = at2
        self.type3 = at3
        self.type4 = at4

    @property
    def name(self):
        return '%s,%s,%s,%s' % (self.type1, self.type2, self.type3, self.type4)

    def __lt__(self, other):
        return [self.type1, self.type2, self.type3, self.type4] \
               < [other.type1, other.type2, other.type3, other.type4]

    def __gt__(self, other):
        return [self.type1, self.type2, self.type3, self.type4] \
               > [other.type1, other.type2, other.type3, other.type4]


class PolarizableTerm(FFTerm):
    '''
    Base class for all polarization terms.

    Subclasses should be implemented for each functional form,
    e.g. :class:`DrudeTerm`.

    Parameters
    ----------
    type : str

    Attributes
    ----------
    type : str
    '''

    def __init__(self, type):
        super().__init__()
        self.type = type

    @property
    def name(self):
        return self.type

    def __lt__(self, other):
        return self.type < other.type

    def __gt__(self, other):
        return self.type > other.type


class LJ126Term(VdwTerm):
    '''
    vdW term in LJ-12-6 function form.

    The energy function is

    >>> U = 4*epsilon*((sigma/r)^12-(sigma/r)^6)

    LJ126 is commonly used, therefore we don't generalize it with :func:`MieTerm`.

    During the initialization, the two atom types will be sorted by their string.

    Parameters
    ----------
    type1 : str
    type2 : str
    epsilon : float
    sigma : float

    Attributes
    ----------
    type1 : str
    type2 : str
    epsilon : float
    sigma : float

    '''

    _zfp_attrs = {
        'type1'  : str,
        'type2'  : str,
        'epsilon': float,
        'sigma'  : float,
    }

    def __init__(self, type1, type2, epsilon, sigma):
        super().__init__(type1, type2)
        self.epsilon = epsilon
        self.sigma = sigma

    def evaluate_energy(self, r):
        return 4 * self.epsilon * ((self.sigma / r) ** 12 - (self.sigma / r) ** 6)


FFTermFactory.register(LJ126Term)


class MieTerm(VdwTerm):
    '''
    vdW term with generalized LJ function form.

    The energy function is

    >>> U = C * epsilon * ((sigma/r)^n - (sigma/r)^m)
    >>> C = n/(n-m) * (n/m)^(m/(n-m))
    >>> r_min = (n/m)^(1/(n-m)) * sigma

    This term is mainly used for Coarse-Grained force field.

    During the initialization, the two atom types will be sorted by their string.

    Parameters
    ----------
    type1 : str
    type2 : str
    epsilon : float
    sigma : float
    repulsion : float
    attraction : float

    Attributes
    ----------
    type1 : str
    type2 : str
    epsilon : float
    sigma : float
    repulsion : float
    attraction : float
    '''

    _zfp_attrs = {
        'type1'     : str,
        'type2'     : str,
        'epsilon'   : float,
        'sigma'     : float,
        'repulsion' : float,
        'attraction': float,
    }

    def __init__(self, type1, type2, epsilon, sigma, repulsion, attraction):
        super().__init__(type1, type2)
        self.epsilon = epsilon
        self.sigma = sigma
        self.repulsion = repulsion
        self.attraction = attraction

    def evaluate_energy(self, r):
        return self.factor_energy() * self.epsilon \
               * ((self.sigma / r) ** self.repulsion - (self.sigma / r) ** self.attraction)

    def factor_energy(self):
        '''
        Get the energy pre-factor of the Mie function.

        >>> C = n/(n-m) * (n/m)^(m/(n-m))

        Returns
        -------
        factor : float
        '''
        rep, att = self.repulsion, self.attraction
        return rep / (rep - att) * (rep / att) ** (att / (rep - att))

    def factor_r_min(self):
        '''
        Get the converting factor from sigma to the distance of energy minimum.

        >>> f = (n/m)^(1/(n-m))

        Returns
        -------
        factor : float
        '''
        rep, att = self.repulsion, self.attraction
        return (rep / att) ** (1 / (rep - att))


FFTermFactory.register(MieTerm)


class HarmonicBondTerm(BondTerm):
    '''
    Bond term in harmonic function form

    The energy function is

    >>> U = k * (b-b0)^2

    During the initialization, the two atom types will be sorted by their string.

    Parameters
    ----------
    type1 : str
    type2 : str
    length : float
    k : float
    fixed : bool

    Attributes
    ----------
    type1 : str
    type2 : str
    length : float
    k : float
    fixed : bool
    '''

    _zfp_attrs = {
        'type1' : str,
        'type2' : str,
        'length': float,
        'k'     : float,
        'fixed' : lambda x: bool(strtobool(x))
    }

    def __init__(self, type1, type2, length, k, fixed=False):
        super().__init__(type1, type2, length, fixed=fixed)
        self.k = k

    def evaluate_energy(self, val):
        return self.k * (val - self.length) ** 2


FFTermFactory.register(HarmonicBondTerm)


class HarmonicAngleTerm(AngleTerm):
    '''
    Angle term in harmonic function form

    The energy function is

    >>> U = k * (theta-theta0)^2

    Be careful that angle is in unit of degree, but the force constant is in unit of kJ/mol/rad^2.

    During the initialization, the two side atom types will be sorted by their string.

    Parameters
    ----------
    type1 : str
    type2 : str
    theta : float
    k : float
    fixed : bool

    Attributes
    ----------
    type1 : str
    type2 : str
    theta : float
    k : float
    fixed : bool
    '''

    _zfp_attrs = {
        'type1': str,
        'type2': str,
        'type3': str,
        'theta': float,
        'k'    : float,
        'fixed': lambda x: bool(strtobool(x))
    }

    def __init__(self, type1, type2, type3, theta, k, fixed=False):
        super().__init__(type1, type2, type3, theta, fixed=fixed)
        self.k = k

    def evaluate_energy(self, val):
        return self.k * ((val - self.theta) / 180 * PI) ** 2


FFTermFactory.register(HarmonicAngleTerm)


class SDKAngleTerm(AngleTerm):
    '''
    Angle term in SDK function form

    The energy function is

    >>> U = k * (theta-theta0)^2 + LJ96
    >>> LJ96 = 6.75 * epsilon * ((sigma/r)^9 - (sigma/r)^6) + epsilon, r < 1.144714 * sigma

    Be careful that angle is in unit of degree, but the force constant is in unit of kJ/mol/rad^2.

    This term itself does not contain parameters `epsilon` and `sigma`.
    Instead, it expect a :class:`MieTerm` between `type1` and `type3` existing in the :class:`ForceField` object.
    If such a MieTerm does not exist, or the repulsion and attraction of this MieTerm do not equal to 9 and 6,
    then the ForceField is invalid and cannot be used to construct a :class:`~mstools.simsys.System`.

    During the initialization, the two side atom types will be sorted by their string.

    Parameters
    ----------
    type1 : str
    type2 : str
    theta : float
    k : float

    Attributes
    ----------
    type1 : str
    type2 : str
    theta : float
    k : float
    fixed : bool
    '''

    _zfp_attrs = {
        'type1': str,
        'type2': str,
        'type3': str,
        'theta': float,
        'k'    : float,
    }

    def __init__(self, type1, type2, type3, theta, k):
        super().__init__(type1, type2, type3, theta, fixed=False)
        self.k = k


FFTermFactory.register(SDKAngleTerm)


class PeriodicDihedralTerm(DihedralTerm):
    '''
    Dihedral term in periodic cosine function form

    The energy function is

    >>> U = \sum^n k_n*(1+cos(n*phi-phi0_n))

    During the initialization, the sequence of atom types to use `i-j-k-l` or `l-k-j-i`
    will be determined by their string order.

    DihedralTerm allows wildcard(*) for side atoms.
    For sorting purpose, the wildcard will always be the last.
    During force field matching, the terms with wildcard will have lower priority.
    The terms with wildcard will be used only if exact match cannot be found.

    PeriodicTermDihedral is initialized without parameters.
    The parameters should be added by calling :func:`add_parameter`.

    Examples
    --------

    >>> term = PeriodicDihedralTerm('h_1', 'c_4', 'c_4', 'h_1')
    >>> term.add_parameter(0.0, 0.6485, 1)
    >>> term.add_parameter(180.0, 1.0678, 2)
    >>> term.add_parameter(0.0, 0.6226, 3)
    >>> for para in term.parameters:
    >>>     print(para.phi, para.k, para.n)
        0.0 0.6485 1
        180.0 1.0678 2
        0.0 0.6226 3
    >>> term.is_opls_convention
        True
    >>> term.get_opls_parameters()
        (0.6485 1.0678 0.6226 0.0)

    Parameters
    ----------
    type1 : str
    type2 : str
    type3 : str
    type4 : str

    Attributes
    ----------
    type1 : str
    type2 : str
    type3 : str
    type4 : str
    parameters : list of namedtuple
        Each element is a namedtuple :attr:`Parameter` describing the parameter for each multiplicity.
    '''

    _zfp_attrs = {
        'type1': str,
        'type2': str,
        'type3': str,
        'type4': str,
    }

    Parameter = namedtuple('Parameter', ('phi', 'k', 'n'))

    def __init__(self, type1, type2, type3, type4):
        super().__init__(type1, type2, type3, type4)
        self.parameters = []

    def add_parameter(self, phi, k, n):
        '''
        Add parameters for a multiplicity to this dihedral term.

        Multiplicity must be a positive integer. Otherwise, an Exception will be raised.
        If there already exists parameter for this multiplicity, an Exception will be raised.

        Parameters
        ----------
        phi : float
            Phase shift for this multiplicity
        k : float
            Force constant
        n : int
            Multiplicity
        '''
        if not isinstance(n, int) or n < 1:
            raise Exception('Multiplicity should be a positive integer: %s' % self.name)
        for para in self.parameters:
            if para.n == n:
                raise Exception('Duplicated multiplicity: %s' % self.name)
        self.parameters.append(self.Parameter(phi=phi, k=k, n=n))
        self.parameters.sort(key=lambda x: x.n)

    def _to_zfp_extra(self) -> {str: str}:
        d = {}
        for para in self.parameters:
            d.update({
                'phi_%i' % para.n: '%.1f' % para.phi,
                'k_%i' % para.n  : '%.4f' % para.k,
            })
        return d

    def _from_zfp_extra(self, d: {str: str}):
        for key in d.keys():
            if key.startswith('phi_'):
                n = int(key.split('_')[-1])
                phi = float(d['phi_%i' % n])
                k = float(d['k_%i' % n])
                self.add_parameter(phi, k, n)

    def evaluate_energy(self, val):
        energy = 0
        for para in self.parameters:
            energy += para.k * (1 + math.cos(para.n * val - para.phi))
        return energy

    @property
    def is_opls_convention(self) -> bool:
        '''
        Whether or not this term follows the OPLS dihedral convention

        In OPLS convention, the largest multiplicity equals to 4.
        The phi_0 for multiplicity (1, 2, 3, 4) equal to (0, 180, 0, 180), respectively.

        If the dihedral follows OPLS convention, the exporting can be cleaner for some package.

        Returns
        -------
        is : bool
        '''
        for para in self.parameters:
            if para.n == 1:
                if para.phi != 0:
                    return False
            elif para.n == 2:
                if para.phi != 180:
                    return False
            elif para.n == 3:
                if para.phi != 0:
                    return False
            elif para.n == 4:
                if para.phi != 180:
                    return False
            else:
                if para.k != 0:
                    return False
        return True

    @property
    def is_zero(self):
        for para in self.parameters:
            if para.k != 0:
                return False
        return True

    def get_opls_parameters(self):
        '''
        Get the four force constants of this dihedral term if it follows OPLS diehdral convention.

        If it does not follow OPLS convention, an Exception will be raised.

        Returns
        -------
        k1 : float
        k2 : float
        k3 : float
        k4 : float
        '''
        k1 = k2 = k3 = k4 = 0.0
        for para in self.parameters:
            if para.n == 1:
                if para.phi != 0:
                    raise Exception(f'{str(self)} does not follow OPLS convention, phi_1 != 0')
                k1 = para.k
            elif para.n == 2:
                if para.phi != 180:
                    raise Exception(f'{str(self)} does not follow OPLS convention, phi_2 != 180')
                k2 = para.k
            elif para.n == 3:
                if para.phi != 0:
                    raise Exception(f'{str(self)} does not follow OPLS convention, phi_3 != 0')
                k3 = para.k
            elif para.n == 4:
                if para.phi != 180:
                    raise Exception(f'{str(self)} does not follow OPLS convention, phi_4 != 180')
                k4 = para.k
            else:
                raise Exception(f'{str(self)} does not follow OPLS convention, n > 4')
        return k1, k2, k3, k4


FFTermFactory.register(PeriodicDihedralTerm)


class OplsImproperTerm(ImproperTerm):
    '''
    Improper term in OPLS cosine function form

    The energy function is

    >>> U = k * (1-cos(2*phi))

    During the initialization, the three side atom types will be sorted by their string.

    ImproperTerm allows wildcard(*) for side atoms.
    During force field matching, the terms with wildcard will have lower priority.
    The terms with wildcard will be used only if exact match cannot be found.

    Care must be taken when exporting OplsImproperTerm.
    For improper a1-a2-a3-a4, a1 is the center atom.
    In OPLS convention, the value of the improper is defined as the angle between plane a2-a3-a1 and a3-a1-a4.

    Parameters
    ----------
    type1 : str
    type2 : str
    type3 : str
    type4 : str
    k : float

    Attributes
    ----------
    type1 : str
    type2 : str
    type3 : str
    type4 : str
    k : float
    '''

    _zfp_attrs = {
        'type1': str,
        'type2': str,
        'type3': str,
        'type4': str,
        'k'    : float,
    }

    def __init__(self, type1, type2, type3, type4, k):
        super().__init__(type1, type2, type3, type4)
        self.k = k

    def evaluate_energy(self, val):
        return self.k * (1 - math.cos(2 * val))


FFTermFactory.register(OplsImproperTerm)


class HarmonicImproperTerm(ImproperTerm):
    '''
    Improper term in harmonic function form. Mainly used by CHARMM.

    The energy function is

    >>> U = k * (phi-phi0)^2

    Be careful that improper is in unit of degree, but the force constant is in unit of kJ/mol/rad^2.

    During the initialization, the three side atom types will be sorted by their string.

    ImproperTerm allows wildcard(*) for side atoms.
    During force field matching, the terms with wildcard will have lower priority.
    The terms with wildcard will be used only if exact match cannot be found.

    Care must be taken when exporting HarmonicImproperTerm.
    For improper a1-a2-a3-a4, a1 is the center atom.
    In CHARMM convention, the improper is defined as the angle between plane a1-a2-a3 and a2-a3-a4.

    Parameters
    ----------
    type1 : str
    type2 : str
    type3 : str
    type4 : str
    phi : float
    k : float

    Attributes
    ----------
    type1 : str
    type2 : str
    type3 : str
    type4 : str
    phi : float
    k : float
    '''

    _zfp_attrs = {
        'type1': str,
        'type2': str,
        'type3': str,
        'type4': str,
        'phi'  : float,
        'k'    : float,
    }

    def __init__(self, type1, type2, type3, type4, phi, k):
        super().__init__(type1, type2, type3, type4)
        self.phi = phi
        self.k = k

    def evaluate_energy(self, val):
        return self.k * ((val - self.phi) / 180 * PI) ** 2


FFTermFactory.register(HarmonicImproperTerm)


class DrudeTerm(PolarizableTerm):
    '''
    Polarization term described by Drude induced dipole.

    Currently, only the isotropic Drude polarization is implemented.
    The energy function for polarization is

    >>> E = k * d^2

    The charge assigned to the Drude particle is

    >>> q = - sqrt(4 * pi * eps_0 * (2k) * alpha)

    If this atom is bonded with hydrogen atoms, the argument `merge_alpha_H` determines the polarizability of neighbour H atoms.
    The alpha of these H atoms will be merged into the this atom.
    Therefore, DrudeTerm for H atom types should not be provided explicitly. Otherwise, there will be double count.
    The H atoms are identified by check the :attr:`~mstools.topology.Atom.symbol` attribute.
    An atom is considered to be hydrogen if symbol equals 'H'.

    Parameters
    ----------
    type : str
    alpha : float
    thole : float
    k : float
    mass : float
    merge_alpha_H : float

    Attributes
    ----------
    type : str
    alpha : float
    thole : float
    k : float
    mass : float
    merge_alpha_H : float
    '''

    _zfp_attrs = {
        'type'         : str,
        'alpha'        : float,
        'thole'        : float,
        'k'            : float,
        'mass'         : float,
        'merge_alpha_H': float,
    }

    def __init__(self, type: str, alpha, thole, k=4184 / 2 * 100, mass=0.4, merge_alpha_H=0.0):
        super().__init__(type)
        self.alpha = alpha  # nm^3
        self.thole = thole
        self.k = k  # kJ/mol/nm^2
        self.mass = mass
        self.merge_alpha_H = merge_alpha_H

    def get_charge(self, alpha=None):
        '''
        Get the charge offset between parent atom and Drude particle.

        The charge assigned on the Drude particle is the negative of this charge offset.

        Parameters
        ----------
        alpha : float
            The polarizability of parent atom in unit of nm^3.

        Returns
        -------
        charge : float
            The charge offset from Drude particle to parent atom.
        '''
        if alpha is None:
            alpha = self.alpha
        factor = math.sqrt(1E-6 / AVOGADRO) / ELEMENTARY_CHARGE
        return math.sqrt(4 * PI * VACUUM_PERMITTIVITY * (2 * self.k) * alpha) * factor


FFTermFactory.register(DrudeTerm)
