"""Run simple cell optimisation"""

"""
Copyright (c) 2016, EPFL/Blue Brain Project

 This file is part of BluePyOpt <https://github.com/BlueBrain/BluePyOpt>

 This library is free software; you can redistribute it and/or modify it under
 the terms of the GNU Lesser General Public License version 3.0 as published
 by the Free Software Foundation.

 This library is distributed in the hope that it will be useful, but WITHOUT
 ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
 FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
 details.

 You should have received a copy of the GNU Lesser General Public License
 along with this library; if not, write to the Free Software Foundation, Inc.,
 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""


# pylint: disable=R0914, W0633

import pickle
import numpy
import bluepyopt.ephys as ephys

# Parameters in release circuit model
release_params = {
    'gNaTs2_tbar_NaTs2_t.apical': 0.026145,
    'gSKv3_1bar_SKv3_1.apical': 0.004226,
    'gImbar_Im.apical': 0.000143,
    'gNaTa_tbar_NaTa_t.axonal': 3.137968,
    'gK_Tstbar_K_Tst.axonal': 0.089259,
    'gamma_CaDynamics_E2.axonal': 0.002910,
    'gNap_Et2bar_Nap_Et2.axonal': 0.006827,
    'gSK_E2bar_SK_E2.axonal': 0.007104,
    'gCa_HVAbar_Ca_HVA.axonal': 0.000990,
    'gK_Pstbar_K_Pst.axonal': 0.973538,
    'gSKv3_1bar_SKv3_1.axonal': 1.021945,
    'decay_CaDynamics_E2.axonal': 287.198731,
    'gCa_LVAstbar_Ca_LVAst.axonal': 0.008752,
    'gamma_CaDynamics_E2.somatic': 0.000609,
    'gSKv3_1bar_SKv3_1.somatic': 0.303472,
    'gSK_E2bar_SK_E2.somatic': 0.008407,
    'gCa_HVAbar_Ca_HVA.somatic': 0.000994,
    'gNaTs2_tbar_NaTs2_t.somatic': 0.983955,
    'decay_CaDynamics_E2.somatic': 210.485284,
    'gCa_LVAstbar_Ca_LVAst.somatic': 0.000333
}


def set_rcoptions(func):
    '''decorator to apply custom matplotlib rc params to function, undo after'''
    import matplotlib

    def wrap(*args, **kwargs):
        """Wrap"""
        options = {'axes.linewidth': 2, }
        with matplotlib.rc_context(rc=options):
            func(*args, **kwargs)
    return wrap


@set_rcoptions
def analyse_cp(opt=None, cp_filename=None, figs=None, boxes=None):
    """Analyse optimisation results"""

    bpop_model_fig, bpop_evol_fig = figs
    bpop_model_box, bpop_evol_box = boxes

    cp = pickle.load(open(cp_filename, "r"))
    results = (
        cp['population'],
        cp['halloffame'],
        cp['history'],
        cp['logbook'])

    _, hof, _, log = results

    print '\nHall of fame'
    print '################'

    plot_validation(opt, [opt.evaluator.param_dict(ind) for ind in hof])

    for _, individual in enumerate(hof[:1], 1):
        # objectives = opt.evaluator.objective_dict(
        #    individual.fitness.values)
        parameter_values = opt.evaluator.param_dict(individual)

        # print '\nIndividual %d' % ind_number
        # print '#############'
        # print 'Parameters: %s' % parameter_values
        # print '\nObjective values: %s' % objectives

        fitness_protocols = opt.evaluator.fitness_protocols
        responses = {}

        nrn = ephys.simulators.NrnSimulator()

        for protocol in fitness_protocols.values():
            response = protocol.run(
                cell_model=opt.evaluator.cell_model,
                param_values=parameter_values,
                sim=nrn)
            responses.update(response)

        box = bpop_model_box
        height = float(box['height']) / 2.0
        responses_height = height * 0.95
        plot_responses(
            responses,
            fig=bpop_model_fig,
            box={
                'left': box['left'],
                'bottom': float(box['height']) - responses_height,
                'width': box['width'],
                'height': responses_height * 0.98})

        objectives = opt.evaluator.fitness_calculator.calculate_scores(
            responses)

        plot_objectives(
            objectives,
            fig=bpop_model_fig,
            box={
                'left': box['left'],
                'bottom': box['bottom'],
                'width': box['width'],
                'height': float(box['height']) / 2.0})

    plot_log(log, fig=bpop_evol_fig,
             box=bpop_evol_box)


def plot_log(log, fig=None, box=None):
    """Plot logbook"""

    gen_numbers = log.select('gen')
    mean = numpy.array(log.select('avg'))
    std = numpy.array(log.select('std'))
    minimum = numpy.array(log.select('min'))

    left_margin = box['width'] * 0.1
    right_margin = box['width'] * 0.05
    top_margin = box['height'] * 0.05
    bottom_margin = box['height'] * 0.1

    axes = fig.add_axes(
        (box['left'] + left_margin,
         box['bottom'] + bottom_margin,
         box['width'] - left_margin - right_margin,
         box['height'] - bottom_margin - top_margin))

    stdminus = mean - std
    stdplus = mean + std
    axes.plot(
        gen_numbers,
        mean,
        color='black',
        linewidth=2,
        label='population average')

    axes.fill_between(
        gen_numbers,
        stdminus,
        stdplus,
        color='lightgray',
        linewidth=2,
        label=r'population standard deviation')

    axes.plot(
        gen_numbers,
        minimum,
        color='red',
        linewidth=2,
        label='population minimum')

    axes.set_xlim(min(gen_numbers) - 1, max(gen_numbers) + 1)
    axes.set_xlabel('Generation #')
    axes.set_ylabel('Sum of objectives')
    axes.set_ylim([0, max(stdplus)])
    axes.legend()


def plot_history(history):
    """Plot the history of the individuals"""

    import networkx

    import matplotlib.pyplot as plt
    plt.figure()

    graph = networkx.DiGraph(history.genealogy_tree)
    graph = graph.reverse()     # Make the grah top-down
    # colors = [\
    #        toolbox.evaluate(history.genealogy_history[i])[0] for i in graph]
    positions = networkx.graphviz_layout(graph, prog="dot")
    networkx.draw(graph, positions)


def plot_objectives(objectives, fig=None, box=None):
    """Plot objectives of the cell model"""

    import collections
    objectives = collections.OrderedDict(sorted(objectives.iteritems()))
    left_margin = box['width'] * 0.4
    right_margin = box['width'] * 0.05
    top_margin = box['height'] * 0.05
    bottom_margin = box['height'] * 0.1

    axes = fig.add_axes(
        (box['left'] + left_margin,
         box['bottom'] + bottom_margin,
         box['width'] - left_margin - right_margin,
         box['height'] - bottom_margin - top_margin))

    ytick_pos = [x + 0.5 for x in range(len(objectives.keys()))]

    axes.barh(ytick_pos,
              objectives.values(),
              height=0.5,
              align='center',
              color='#779ECB')
    axes.set_yticks(ytick_pos)
    axes.set_yticklabels(objectives.keys(), size='x-small')
    axes.set_ylim(-0.5, len(objectives.values()) + 0.5)
    axes.set_xlabel('Objective value (# std)')
    axes.set_ylabel('Objectives')


def plot_responses(responses, fig=None, box=None):
    """Plot responses of the cell model"""

    rec_rect = {}
    rec_rect['left'] = box['left']
    rec_rect['width'] = box['width']
    rec_rect['height'] = float(box['height']) / len(responses)
    rec_rect['bottom'] = box['bottom'] + \
        box['height'] - rec_rect['height']

    last = len(responses) - 1
    for i, (_, recording) in enumerate(sorted(responses.items())):
        plot_recording(recording, fig=fig, box=rec_rect, xlabel=(last == i))
        rec_rect['bottom'] -= rec_rect['height']


def plot_recording(recording, fig=None, box=None, xlabel=False):
    """Plot responses of the cell model"""

    import matplotlib.pyplot as plt

    left_margin = box['width'] * 0.25
    right_margin = box['width'] * 0.05
    top_margin = box['height'] * 0.1
    bottom_margin = box['height'] * 0.25

    axes = fig.add_axes(
        (box['left'] + left_margin,
         box['bottom'] + bottom_margin,
         box['width'] - left_margin - right_margin,
         box['height'] - bottom_margin - top_margin))
    recording.plot(axes)
    axes.set_ylim(-100, 40)
    axes.spines['top'].set_visible(False)
    axes.spines['right'].set_visible(False)
    axes.tick_params(
        axis='both',
        bottom='on',
        top='off',
        left='on',
        right='off')

    name = recording.name
    if name.endswith('.v'):
        name = name[:-2]

    axes.set_ylabel(name + '\n(mV)', rotation=0, labelpad=25)
    yloc = plt.MaxNLocator(2)
    axes.yaxis.set_major_locator(yloc)

    if xlabel:
        axes.set_xlabel('Time (ms)')


def plot_validation(opt, parameters):
    """Plot validation"""

    soma_loc = ephys.locations.NrnSeclistCompLocation(
        name='soma',
        seclist_name='somatic',
        sec_index=0,
        comp_x=0.5)

    validation_recording = ephys.recordings.CompRecording(
        name='validation.soma.v',
        location=soma_loc,
        variable='v')

    validation_i_data = numpy.loadtxt('exp_data/noise_i.txt')
    # validation_v_data = numpy.loadtxt('exp_data/noise_v.txt')
    validation_time = validation_i_data[:, 0] + 200.0
    validation_current = validation_i_data[:, 1]
    # validation_voltage = validation_v_data[:, 1]
    validation_stimulus = ephys.stimuli.NrnCurrentPlayStimulus(
        current_points=validation_current,
        time_points=validation_time,
        location=soma_loc)
    hypamp_stimulus = ephys.stimuli.NrnSquarePulse(
        step_amplitude=-0.126,
        step_delay=0,
        step_duration=max(validation_time),
        location=soma_loc,
        total_duration=max(validation_time))

    validation_protocol = ephys.protocols.SweepProtocol(
        'validation',
        [validation_stimulus, hypamp_stimulus],
        [validation_recording])

    validation_responses = {}
    write_pickle = False

    paramsets = {}
    paramsets['release'] = release_params
    for index, param_values in enumerate(parameters):
        paramsets['model%d' % index] = param_values

    if write_pickle:
        for paramset_name, paramset in paramsets.items():
            validation_responses[paramset_name] = opt.evaluator.run_protocols(
                [validation_protocol],
                param_values=paramset)

        pickle.dump(validation_responses, open('validation_response.pkl', 'w'))
    else:
        validation_responses = pickle.load(open('validation_response.pkl'))
    # print validation_responses['validation.soma.v']['time']

    peaktimes = {}
    import efel
    for index, model_name in enumerate(validation_responses.keys()):
        trace = {}
        trace['T'] = validation_responses[
            model_name]['validation.soma.v']['time']
        trace['V'] = validation_responses[model_name][
            'validation.soma.v']['voltage']
        trace['stim_start'] = [500]
        trace['stim_end'] = [max(validation_time)]
        peaktimes[model_name] = efel.getFeatureValues(
            [trace],
            ['peak_time'])[0]['peak_time']

    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(3, figsize=(10, 7), facecolor='white', sharex=True)

    ax[0].plot(validation_time, validation_current, 'k')
    ax[0].spines['top'].set_visible(False)
    ax[0].spines['right'].set_visible(False)
    ax[0].spines['bottom'].set_visible(False)
    ax[0].tick_params(
        axis='both',
        bottom='off',
        top='off',
        left='on',
        right='off')
    ax[0].set_ylabel('Current\n (nA)', rotation=0, labelpad=25)

    for index, (model_name, peak_time) in enumerate(sorted(peaktimes.items())):
        print model_name
        if model_name == 'release':
            color = 'red'
            print color, peak_time
        elif model_name == 'model0':
            color = 'darkblue'
        else:
            color = 'lightblue'
        ax[1].scatter(
            peak_time,
            numpy.array(
                [100] *
                len(peak_time)) +
            10 *
            index,
            color=color,
            s=10)
    ax[1].spines['top'].set_visible(False)
    ax[1].spines['right'].set_visible(False)
    ax[1].spines['bottom'].set_visible(False)
    ax[1].spines['left'].set_visible(False)
    ax[1].tick_params(
        bottom='off',
        top='off',
        left='off',
        right='off')
    ax[1].set_yticks([])

    ax[2].plot(
        validation_responses['release']['validation.soma.v']['time'],
        validation_responses['release']['validation.soma.v']['voltage'], 'r',
        linewidth=1)

    ax[2].plot(
        validation_responses[
            'model0']['validation.soma.v']['time'],
        validation_responses[
            'model0']['validation.soma.v']['voltage'],
        color='darkblue',
        linewidth=1)

    ax[2].spines['top'].set_visible(False)
    ax[2].spines['right'].set_visible(False)
    ax[2].tick_params(
        axis='both',
        bottom='on',
        top='off',
        left='on',
        right='off')

    ax[2].set_yticks([-100, 0.0])
    ax[2].set_ylabel('Voltage\n (mV)', rotation=0, labelpad=25)
    ax[2].set_xlabel('Time (ms)')
    ax[2].set_xlim(min(validation_time), max(validation_time))

    fig.tight_layout()

    fig.savefig('figures/l5pc_valid.eps')


@set_rcoptions
def analyse_releasecircuit_model(opt, fig=None, box=None):
    """Analyse L5PC model from release circuit"""

    fitness_protocols = opt.evaluator.fitness_protocols

    responses = opt.evaluator.run_protocols(
        opt.evaluator.fitness_protocols,
        param_values=release_params)

    height = float(box['height']) / 2.0
    responses_height = height * 0.95
    plot_responses(responses, fig=fig,
                   box={
                       'left': box['left'],
                       'bottom': float(box['height']) - responses_height,
                       'width': box['width'],
                       'height': responses_height * 0.98})

    responses = {}
    nrn = ephys.simulators.NrnSimulator()

    for protocol in fitness_protocols.values():
        response = protocol.run(
            cell_model=opt.evaluator.cell_model,
            param_values=release_params,
            sim=nrn)
        responses.update(response)

    objectives = opt.evaluator.fitness_calculator.calculate_scores(
        responses)

    height = float(box['height']) / 2.0
    responses_height = height * 0.95
    plot_responses(responses, fig=fig,
                   box={
                       'left': box['left'],
                       'bottom': float(box['height']) - responses_height,
                       'width': box['width'],
                       'height': responses_height * 0.98})

    plot_objectives(objectives, fig=fig,
                    box={
                        'left': box['left'],
                        'bottom': box['bottom'],
                        'width': box['width'],
                        'height': height})


def analyse_releasecircuit_hocmodel(opt, fig=None, box=None):
    """Analyse L5PC model from release circuit from .hoc template"""

    fitness_protocols = opt.evaluator.fitness_protocols

    from hocmodel import HocModel  # NOQA

    template_model = HocModel(morphname="./morphology/C060114A7.asc",
                              template="./cADpyr_76.hoc")

    responses = template_model.run_protocols(
        fitness_protocols)

    objectives = opt.evaluator.fitness_calculator.calculate_scores(
        responses)

    # template_model.instantiate()
    # for section in template_model.icell.axonal:
    #    print section.L, section.diam, section.nseg

    plot_responses(responses, fig=fig,
                   box={
                       'left': box['left'],
                       'bottom': box['bottom'] + float(box['height']) / 2.0,
                       'width': box['width'],
                       'height': float(box['height']) / 2.0})

    plot_objectives(objectives, fig=fig,
                    box={
                        'left': box['left'],
                        'bottom': box['bottom'],
                        'width': box['width'],
                        'height': float(box['height']) / 2.0})
