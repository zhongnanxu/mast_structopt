# Copyright (C) 2016 - Zhongnan Xu
'''This contains the mast_structopt class calculator for running structopt through MAST. Outside of running calculations, this file contains functions for organizing, reading, and writing data'''

import os

from ase.calculators.general import Calculator

from mast_structopt_rc import *
from mast_structopt_exceptions import *

class Mast_Structopt(Calculator):
    '''This is an ase.calculator class that allows the use of structopt
    and mast through ase'''

    def __init__(self, calcdir=None, **kwargs):
        if calcdir==None:
            self.calcdir = os.getcwd()
        else:
            self.calcdir = os.path.expanduser(calcdir)
        self.cwd = os.getcwd()
        self.kwargs = kwargs

        # If we are not using the context manager, then we have to
        # initialize the atoms. If we are, __enter__ will evaluate
        # and atoms are initialized there.
        if calcdir==None:
            self.initialize(**self.kwargs)

    def __enter__(self):
        '''On enter, make sure directory exists. Create it if necessary
        and change into the directory. Then return the calculator.'''

        # Make directory if it doesn't already exist
        if not os.path.isdir(self.calcdir):
            os.makedirs(self.calcdir)

        # Now change into the new working directory
        os.chdir(self.calcdir)
        self.initialize(**self.kwargs)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        '''On exit, change back to the original directory'''

        os.chdir(self.cwd)

        return

    def initialize(self, **kwargs):
        '''We need an extra initialize because things are only done once
        we are inside the directory. The objectives of this function are...

        1. Set some additional run paramaters. These parameters are kept
        different because we don't want them initializing another run

        2. Get the status of the calculation. Generally, these fall into
        clean, running, finished, error. If it is not clean, it should
        read the input file and store them. 

        3. Set the new kwargs (if they are new).'''

        self.real_params = {}
        self.string_params = {}
        self.int_params = {}
        self.bool_params = {}
        self.list_params = {}
        for key in real_keys:
            self.real_params[key] = None
        for key in string_keys:
            self.string_params[key] = None
        for key in int_keys:
            self.int_params[key] = None
        for key in bool_keys:
            self.bool_params[key] = None
        for key in list_keys:
            self.list_params[key] = None


        self.run_params = {'nodes': 1,
                           'walltime': 24,
                           'ppn': None,
                           'mast_exec': 'python',
                           'queue': None,
                           'write_method': 'write_singlerun',
                           'ready_method': 'ready_singlerun',
                           'run_method': 'run_singlerun',
                           'complete_method': 'complete_singlerun',
                           'update_children_method': 'give_structure',
                           'program': 'structopt'}
    
        # Now we go through logic to see what to do
        # First check if this is clean directory
        if not os.path.exists('mast_structopt.inp'):
            self.mast_structopt_running = False
            self.converged = False
            self.status = 'empty'

        # If there's only an input file and never got submitted
        elif (os.path.exists('mast_structopt.inp')
              and not os.path.exists('jobdir')
              and not os.path.exists('SUMMARY.txt')):
            self.read_input()
            self.mast_structopt_running = False
            self.converged = False
            self.status = 'empty'

        # If it is running or queued
        elif (os.path.exists('mast_structopt.inp')
              and os.path.exists('jobdir')
              and self.job_in_queue()):
            self.read_input()
            self.mast_structopt_running = False
            self.converged = False
            self.status = 'running'

        # If job is done and this is our first time looking at it
        elif (os.path.exists('mast_structopt.inp')
              and os.path.exists('jobdir')
              and not self.job_in_queue()):
            self.read_input()
            self.copy_output()
            self.read_output()
            self.status = 'done'

        # If the job is done we're looking at it again
        elif (os.path.exists('mast_structupt.inp')
              and os.path.exists('SUMMARY.txt')):
            self.read_input()
            self.read_output()
            self.status = 'done'

        # We want to alert the user of weird directories
        else:
            raise Mast_StructoptUnknownState

        # Store the old parameters read from files for restart purposes
        # Note run_params are not stored since we don't want a change
        # in a run command to produce a re-run
        self.old_real_params = self.real_params.copy()
        self.old_string_params = self.string_params.copy()
        self.old_int_params = self.int_params.copy()
        self.old_bool_params = self.bool_params.copy()
        self.old_list_params = self.list_params.copy()

        # We first set the default keys. Then we set the ones custom
        self.set(**INP_DEFAULTS)
        self.set(**kwargs)

        return

    def set_ppn(self, queue):
        '''The purpose of this function is to automatically set the ppn
        depending on which queue we ask for'''
        if queue == 'morgan1':
            return 8
        elif queue in ['morgan.q', 'morgan2', 'morganeth.q']:
            return 12
        elif queue == 'morgan3':
            return 32
        else:
            raise ValueError('Queue not found: ' + queue)            


    def job_in_queue(self, obdir_file='jobdir'):
        '''This function checks if the job is in the queue. This is tricky
        because of how MAST works. The best way to do this is to check if 
        the folder in the $HOME/MAST/SCRATCH directory is present'''
        with open('jobdir', 'r') as f:
            self.jobdir = f.readline()
        if os.path.exists(self.jobdir):
            return True
        else:
            return False

    def copy_output(self):
        '''This function reads the running file and sees if the directory
        $HOME/MAST/SCRATCH/<running-file-contents> exists. If it does, 
        then the calculation is still running. If not, then it copies the
        output from $HOME/MAST/ARCHIVE/<running-file-contents> into this 
        directory'''

    def set(self, **kwargs):
        '''This function sets the keywords given a dictionary. It overwrites
        values that are different'''

        for key in kwargs:
            if self.real_params.has_key(key):
                self.real_params[key] = kwargs[key]
            elif self.string_params.has_key(key):
                self.string_params[key] = kwargs[key]
            elif self.int_params.has_key(key):
                self.int_params[key] = kwargs[key]
            elif self.bool_params.has_key(key):
                self.bool_params[key] = kwargs[key]
            elif self.list_params.has_key(key):
                self.list_params[key] = kwargs[key]
            elif self.run_params.has_key(key):
                self.run_params[key] = kwargs[key]
            else:
                raise TypeError('Parameter not defined: ' + key)
        return

    def calculate(self):
        '''Generate necessary files in working directory and run
        mast'''

        if self.status == 'running':
            raise Mast_StructoptRunning('Running', os.getcwd())
        if (self.status == 'done'
            and self.converged == False):
            raise Mast_StructoptNotConverged('Not Converged', os.getcwd())
        if self.calculation_required():
            self.write_input()
            self.run()
            self.status = 'running'
        return
        
    
    def write_input(self):
        '''This function writes the input file. The default name is
        mast_structopt.inp'''

        in_file = open('mast_structopt.in', 'w')

        # First write the system_name variable. This will be taken
        # as the calcdir. We only want the last directory.
        self.system_name = os.path.basename(self.calcdir)
        in_file.write('$mast\nsystem_name {0}\n$end\n\n'.format(self.system_name))
        
        # Now we write keywords under the ingredients tags.
        # All of the specified kwargs (except calcdir) are put in here
        in_file.write('$ingredients\nbegin GAlammps\n')

        # First write MAST parameters. Some of these shouldn't change
        in_file.write('\n# Mast Parameters\n')
        for key in self.run_params:
            if isinstance(self.run_params[key], float):
                in_file.write('mast_{0} {1:.8g\n}'.format(key, self.run_params[key]))
            elif isinstance(self.run_params[key], (str, bool, int)):
                in_file.write('mast_{0} {1}\n'.format(key, self.run_params[key]))
            else:
                raise TypeError('Run parameter is wrong type: ', key)


        # Finish writing the ingredients filen
        in_file.write('end\n')
        in_file.write('$end\n')
            
        return

    def run(self):
        return

    def calculation_required(self):
        return True
