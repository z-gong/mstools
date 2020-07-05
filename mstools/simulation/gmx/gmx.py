import os

from ..simulation import Simulation
from ...wrapper import GMX
from ...utils import get_last_line


class GmxSimulation(Simulation):
    '''
    Base class of predefined simulation protocols with GROMACS.

    Parameters
    ----------
    packmol : Packmol
    dff : DFF
    gmx : GMX
    jobmanager : subclass of JobManager
    packmol_bin : str, optional
        Binary of packmol. Deprecated.
    dff_root : str, optional
        Root directory of DFF. Deprecated.
    dff_db : str, optional
        Default database of DFF. Deprecated.
    dff_table : str, optional
        Default table of DFF. Deprecated.
    gmx_bin : str, optional
        Binary of gmx. Deprecated.
    gmx_mdrun: str, optional
        Binary of gmx mdrun. Deprecated.
    '''
    def __init__(self, packmol=None, dff=None, gmx=None, packmol_bin=None, dff_root=None, gmx_bin=None, gmx_mdrun=None, jobmanager=None, **kwargs):
        super().__init__(packmol=packmol, dff=dff, packmol_bin=packmol_bin, dff_root=dff_root, jobmanager=jobmanager, **kwargs)
        if gmx is not None:
            self.gmx = gmx
        else:
            self.gmx = GMX(gmx_bin=gmx_bin, gmx_mdrun=gmx_mdrun)
        self.logs = []  # used for checking whether the job is successfully finished

    def export(self, gro_out='conf.gro', top_out='topol.top', mdp_out='grompp.mdp', ppf=None, ff=None):
        '''
        Export the topology, force field files and control script for GROMACS.

        Parameters
        ----------
        gro_out : str
        top_out : str
        mdp_out : str
        ppf : str, optional
            PPF file to use. If not provided, will checkout PPF from DFF database.
        ff : str, optional
            The DFF force field table to use for checking out force field.
            If not provided, will use the default table of DFF.
        '''
        print('Generate GROMACS files ...')
        msd = self.msd
        self.dff.set_formal_charge([msd])
        if ppf is not None:
            self.dff.typing([msd])  # in order to set the atom type
            self.dff.set_charge([msd], ppf)
            self.dff.export_gromacs(msd, ppf, gro_out, top_out, mdp_out)
        else:
            ppf_out = 'ff.ppf'
            self.dff.checkout([msd], table=ff, ppf_out=ppf_out)
            self.dff.export_gromacs(msd, ppf_out, gro_out, top_out, mdp_out)

    def fast_export_single(self, gro_out='conf.gro', top_out='topol.top', mdp_out='grompp.mdp', ppf=None, ff=None):
        '''
        Export the topology, force field files and control script for GROMACS using a small simulation box.

        When the simulation box is big, it takes long time for DFF to export files.
        Therefore, a small box which contains only one molecule is built.
        After exporting files with this small box,
        the topology file should be modified to match the size of original simulation box.

        Parameters
        ----------
        gro_out : str
        top_out : str
        mdp_out : str
        ppf : str, optional
            PPF file to use. If not provided, will checkout PPF from DFF database.
        ff : str, optional
            The DFF force field table to use for checking out force field.
            If not provided, will use the default table of DFF.
        '''
        print('Generate GROMACS files ...')
        msd = self._single_msd
        self.dff.set_formal_charge([msd])
        if ppf is not None:
            self.dff.typing([msd])  # in order to set the atom type
            self.dff.set_charge([msd], ppf)
            self.dff.export_gromacs(msd, ppf, gro_out, top_out, mdp_out)
        else:
            ppf_out = 'ff.ppf'
            self.dff.checkout([msd], table=ff, ppf_out=ppf_out)
            self.dff.export_gromacs(msd, ppf_out, gro_out, top_out, mdp_out)

    def check_finished(self, logs=None):
        '''
        Check whether or not the GROMACS simulation is successfully finished.

        The log files generated by GROMACS simulation will be checked.
        The simulation is considered as finished only if the last lines of all log files start with 'Finished mdrun'.

        Parameters
        ----------
        logs : list of str

        Returns
        -------
        finished : bool
        '''
        if logs is None:
            logs = self.logs
        for log in logs:
            if not os.path.exists(log):
                return False
            try:
                last_line = get_last_line(log)
            except:
                return False
            if not last_line.startswith('Finished mdrun'):
                return False
        return True
