import simtk.openmm as mm
from simtk.openmm import app
from simtk.unit import kelvin, bar, nanometer as nm, picosecond as ps
from simtk.unit import kilojoule_per_mole as kJ_mol, kilocalorie_per_mole as kcal_mol
from .grofile import GroFile


def print_omm_info():
    print(mm.__version__)
    print(mm.version.openmm_library_path)
    print([mm.Platform.getPlatform(i).getName() for i in range(mm.Platform.getNumPlatforms())])
    print(mm.Platform.getPluginLoadFailures())


def minimize(sim, tolerance, gro_out=None):
    state = sim.context.getState(getEnergy=True)
    print('Initial energy:', state.getPotentialEnergy())
    sim.minimizeEnergy(tolerance=tolerance * kJ_mol)
    state = sim.context.getState(getPositions=True, getEnergy=True)
    print('Minimized energy:', state.getPotentialEnergy())

    if gro_out is not None:
        GroFile.writeFile(sim.topology, state.getPositions(), state.getPeriodicBoxVectors(),
                          gro_out)


def apply_mc_barostat(system, pcoupl, P, T, nsteps=100):
    if pcoupl == 'iso':
        print('Isotropic barostat')
        system.addForce(mm.MonteCarloBarostat(P * bar, T * kelvin, nsteps))
    elif pcoupl == 'semi-iso':
        print('Anisotropic barostat with coupled XY')
        system.addForce(mm.MonteCarloMembraneBarostat(P * bar, 0 * bar * nm, T * kelvin,
                                                      mm.MonteCarloMembraneBarostat.XYIsotropic,
                                                      mm.MonteCarloMembraneBarostat.ZFree, nsteps))
    elif pcoupl == 'xyz':
        print('Anisotropic barostat')
        system.addForce(
            mm.MonteCarloAnisotropicBarostat([P * bar] * 3, T * kelvin, True, True, True, nsteps))
    elif pcoupl == 'xy':
        print('Anisotropic barostat only for X and Y')
        system.addForce(
            mm.MonteCarloAnisotropicBarostat([P * bar] * 3, T * kelvin, True, True, False, nsteps))
    elif pcoupl == 'z':
        print('Anisotropic barostat only for Z')
        system.addForce(
            mm.MonteCarloAnisotropicBarostat([P * bar] * 3, T * kelvin, False, False, True, nsteps))
    else:
        raise Exception('Available pressure coupling types: iso, semi-iso, xyz, xy, z')


def energy_decomposition(sim: app.Simulation, groups=None):
    if groups is None:
        groups = range(32)
    for group in groups:
        energy = sim.context.getState(getEnergy=True, groups={group}).getPotentialEnergy()
        if energy.value_in_unit(kJ_mol) != 0 or group < 10:
            print('E_%i:' % group, energy)
