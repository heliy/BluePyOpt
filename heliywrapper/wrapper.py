import sys
from datetime import datetime

import multiprocessing
import multiprocessing.pool

import bluepyopt as bpopt
import bluepyopt.ephys as ephys
from bluepyopt.deapext.optimisations import DEAPOptimisation

import json

from configure import *
from buildcell import create_cell
from evaluator import *

class NoDaemonProcess(multiprocessing.Process):
    # make 'daemon' attribute always return False
    def _get_daemon(self):
        return False
    def _set_daemon(self, value):
        pass
    daemon = property(_get_daemon, _set_daemon)

class NoDaemonProcessPool(multiprocessing.pool.Pool):
    Process = NoDaemonProcess

def main(jsonfile):
    with open(jsonfile) as json_data_file:
        conf = json.load(json_data_file)
    
    cell = create_cell(conf[CELL][NAME], conf[INPUT_FILE][MORPHOLOGY],
                       conf[INPUT_FILE][MECHANISMS], conf[INPUT_FILE][PARAMETERS])
    
    protocols = define_protocols(conf[INPUT_FILE][PROTOCOLS])
    fitness_calculator = define_fitness_calculator(conf[INPUT_FILE][FEATURES],
                                                   protocols, conf[THRESHOLDS])
    param_names = [param.name for param in cell.params.values() if not param.frozen]      
    print('sim')
    sim = ephys.simulators.NrnSimulator()
    print("evaluator")
    evaluator = ephys.evaluators.CellEvaluator(cell_model=cell, param_names=param_names,
                                               fitness_protocols=protocols,
                                               fitness_calculator=fitness_calculator,
                                               sim=sim)
    print('create pools ...')
    pool = NoDaemonProcessPool(conf[OPTIMIZE][POOL])
    print("now opt ...")
    opt = bpopt.optimisations.DEAPOptimisation(evaluator=evaluator,
                                               use_scoop = False,
                                               offspring_size=conf[OPTIMIZE][OFFSPRING],
                                               map_function=pool.map) 
    print('now eva ...')
    final_pop, halloffame, log, hist = opt.run(max_ngen=conf[OPTIMIZE][NGEN])
    for i, hof in enumerate(halloffame[:conf[RUN][BEST]]):
        best_params = evaluator.param_dict(hof)
        fitness = evaluator.evaluate_with_dicts(best_params)
        print("")
        print("BEST\tParameter\tValue:")
        for parameter, value in best_params.iteritems():
            print("%d\t%s\t%f" % (i+1, parameter, value))
        print("")
        print('BEST\tFeature Name\tFitness value:')
        for feature, value in fitness.iteritems():
            print("%d\t%s\t%f" % (i+1, feature, value))
    print("")
    print("Optimize Log")
    print(log)
    print("")

if __name__ == "__main__":
    jsonfile = sys.argv[1]
    begin = datetime.now()
    main(jsonfile)
    end = datetime.now()
    print("BEGIN: " + str(begin))
    print("END: " + str(end))
    print("TOTAL TIME: " + str(end-begin))
