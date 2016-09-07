"""
build cell from config files

"""

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

import json
import os

import bluepyopt.ephys as ephys
from bluepyopt.ephys.models import CellModel as PreModel


def define_mechanisms(mechanism_file):
    """Define mechanisms"""

    mech_definitions = json.load(open(mechanism_file))

    mechanisms = []
    for sectionlist, channels in mech_definitions.iteritems():
        seclist_loc = ephys.locations.NrnSeclistLocation(
            sectionlist,
            seclist_name=sectionlist)
        for channel in channels:
            mechanisms.append(ephys.mechanisms.NrnMODMechanism(
                name='%s.%s' % (channel, sectionlist),
                mod_path=None,
                prefix=channel,
                locations=[seclist_loc],
                preloaded=True))

    print('\n'.join('%s' % mech for mech in mechanisms))
    return mechanisms


def define_parameters(parameter_file):
    param_configs = json.load(open(parameter_file))
    parameters = []

    somatic_loc = ephys.locations.NrnSeclistLocation(
            'somatic', seclist_name='somatic')
    apical_loc = ephys.locations.NrnSeclistLocation(
            'apical', seclist_name='apical')
    axonal_loc = ephys.locations.NrnSeclistLocation(
            'axonal', seclist_name='axonal')
    basal_loc = ephys.locations.NrnSeclistLocation(
            'basal', seclist_name='basal')

    for param_config in param_configs:
        if "type" not in param_config:
            raise Exception("must set type of parameters in %s" % param_config["param_name"])

        # get locations of parameter
        locations = [somatic_loc, apical_loc, axonal_loc, basal_loc]
        if "location" in param_config:
            name = param_config['param_name']+"."+param_config["location"]
            if param_config["location"] in ["somatic", "apical", "axonal", "basal"]:
                locations = [ephys.locations.NrnSeclistLocation(
                    param_config["location"],
                    seclist_name = param_config["location"]
                )]
            elif param_config["location"] == 'dendrite':
                locations = [apical_loc, basal_loc]
            elif param_config["location"] != 'all':
                raise Exception("Unkown location position in %s" % param_config["param_name"])
        else:
            if param_config["type"] != "global":
                name = param_config['param_name']+".all"
            else:
                name = param_config['param_name']

        # see if value is fixed
        if "value" in param_config:
            bounds = None
            frozen = True
            value = param_config["value"]
        else:
            value = None
            frozen = False
            if "init" in param_config:
                v = param_config["init"]
                bounds = [v*0.1, v*10]
            elif "bounds" in param_config:
                bounds = param_config["bounds"]
            else:
                raise Exception(
                    "You need decide bounds for parameter %s" % param_config["param_name"])

        print(name)
        if param_config["type"] == "global":
            parameters.append(
                ephys.parameters.NrnGlobalParameter(name=name,
                    param_name=param_config['param_name'],
                    frozen=frozen, value=value))
        elif param_config["type"] == "range":
            parameters.append(
                ephys.parameters.NrnRangeParameter(name=name,
                    param_name=param_config['param_name'],
                    frozen=frozen, bounds=bounds,
                    value=value, locations=locations))
        elif param_config["type"] == "section":
            parameters.append(
                ephys.parameters.NrnSectionParameter(name=name,
                    param_name=param_config['param_name'],
                    frozen=frozen, bounds=bounds,
                    value=value, locations=locations))            
        else:
            raise Exception(
                'parameters type error %s' % param_config['param_name'])
                
    return parameters

def define_morphology(morph_file):
    """Define morphology"""

    return ephys.morphologies.NrnFileMorphology(
        morph_file)


class CellModel(PreModel):
    def instantiate(self, sim=None):
        morph_file = self.morphology.morphology_path
        morph_ext = morph_file.split('.')[-1].lower()
        if morph_ext == "hoc":
            hoc_template = open(morph_file).read()
            sim.neuron.h(hoc_template)
            name = hoc_template.split("endtemplate")[1]
            if "//" in name:
                name = name.split("//")[0]
            name = name.replace(" ", "")
            name = name.replace("\n", "")
            print(name)            
            template_function = getattr(sim.neuron.h, name)
            self.icell = template_function()
        elif morph_ext in ["asc", "swc"]:
            if not hasattr(sim.neuron.h, "Cell"):
                self.icell = self.create_empty_cell("Cell", sim=sim)
            else:
                self.icell = sim.neuron.h.Cell()
            self.morphology.instantiate(sim=sim, icell=self.icell)
        else:
            raise Exception("Unknown Morphology File Type %s " % morph_file)
        
        for mechanism in self.mechanisms:
            mechanism.instantiate(sim=sim, icell=self.icell)
        for param in self.params.values():
            param.instantiate(sim=sim, icell=self.icell)        

def create_cell(cname, morph_file, mechanism_file, parameter_file):
    """Create cell model"""

    cell = CellModel(
        cname,
        morph=define_morphology(morph_file),
        mechs=define_mechanisms(mechanism_file),
        params=define_parameters(parameter_file))

    return cell
