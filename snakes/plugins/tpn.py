# -*- coding: utf-8 -*-
"""
    >>> nets = snakes.plugins.load('tpn', 'snakes.nets', 'nets')
    >>> from nets import *
    >>> n = PetriNet('timed')
    >>> n.add_place(Place('p', ['dot']))
    >>> n.add_transition(Transition('t', min_time=1.0, max_time=2.0))
    >>> t = n.transition('t')
    >>> n.add_input('p', 't', Value('dot'))
    >>> n.reset()
    >>> n.time(0.5)
    0.5
    >>> t.time, t.enabled(Substitution())
    (0.5, False)
    >>> n.time(1.0)
    0.5
    >>> t.time, t.enabled(Substitution())
    (1.0, True)
    >>> n.time(1.0)
    1.0
    >>> t.time, t.enabled(Substitution())
    (2.0, True)
    >>> n.time(1.0)
    0.0
"""
from snakes.nets import ConstraintError
from snakes.plugins import plugin, new_instance
from snakes.pnml import Tree, SnakesError

@plugin("snakes.nets")
def extend(module):
    class Transition(module.Transition):
        def __init__(self, name, guard=None, **kwargs):
            self.time = None                              # elapsed time
            self.min_time = kwargs.pop('min_time', 0.0)   # min duration
            self.max_time = kwargs.pop('max_time', None)  # max duration
            module.Transition.__init__(self, name, guard, **kwargs)

        def __repr__ (self) :
            return "{}({}, {}, 'min_time={}, max_time={}')".format(
                self.__class__.__name__,
                repr(self.name),
                repr(self.guard),
                str(self.min_time),
                str(self.max_time))

        def enabled(self, binding, **kwargs):
            if kwargs.pop("untimed", False):  # untimed transition
                return module.Transition.enabled(self, binding)
            elif self.time is None:  # it's not enabled by places
                return False
            elif self.max_time is None:  # maximum duration is not bounded
                return (self.time >= self.min_time) \
                    and module.Transition.enabled(self, binding)
            else:
                return (self.min_time <= self.time <= self.max_time) \
                    and module.Transition.enabled(self, binding)

        def __pnmldump__ (self):
            t = module.Transition.__pnmldump__(self)

            t.add_child(Tree("min_time", None, Tree.from_obj(self.min_time)))

            if self.max_time is not None:
                t.add_child(Tree("max_time", None,
                                 Tree.from_obj(self.max_time)))

            return t

        @classmethod
        def __pnmlload__ (cls, tree) :
            result = new_instance(cls, module.Transition.__pnmlload__(tree))

            # time
            result.time = None

            # minimum duration
            try :
                result.min_time = tree.child("min_time").child().to_obj()
            except SnakesError :
                result.min_time = 0.0

            # maximum duration
            try :
                result.max_time = tree.child("max_time").child().to_obj()
            except SnakesError :
                result.max_time = None

            return result

    class Place(module.Place):
        def __init__(self, name, tokens=[], check=None, **kwargs):
            self.post = {}
            self.pre = {}
            module.Place.__init__(self, name, tokens, check, **kwargs)

        def reset(self, tokens):
            module.Place.reset(self, tokens)
            for name in self.post:
                trans = self.net.transition(name)
                if len(trans. modes()) > 0:
                    trans.time = 0.0
                else:
                    trans.time = None

        def empty(self):
            module.Place.empty(self)
            for name in self.post:
                self.net.transition(name).time = None

        def _post_enabled(self):
            return dict((name, self.net.transition(name).time is not None)
                        for name in self.post)

        def add(self, tokens):
            enabled = self._post_enabled()
            module.Place.add(self, tokens)
            for name in self.post:
                if not enabled[name]:
                    trans = self.net.transition(name)
                    if len(trans.modes()) > 0:
                        trans.time = 0.0

        def remove(self, tokens):
            enabled = self._post_enabled()
            module.Place.remove(self, tokens)
            for name in self.post:
                if enabled[name]:
                    trans = self.net.transition(name)
                    if len(trans.modes()) == 0:
                        trans.time = None

    class PetriNet(module.PetriNet):
        def reset(self):
            self.set_marking(self.get_marking())

        def step(self):
            step = None
            for trans in self.transition():
                if trans.time is None:
                    continue
                if trans.time < trans.min_time:
                    if step is None:
                        step = trans.min_time - trans.time
                    else:
                        step = min(step, trans.min_time - trans.time)
                elif trans.max_time is None:
                    pass
                elif trans.time <= trans.max_time:
                    if step is None:
                        step = trans.max_time - trans.time
                    else:
                        step = min(step, trans.max_time - trans.time)
            return step

        def time(self, step=None):
            if step is None:
                step = self.step()
                if step is None:
                    return None
            enabled = []
            for trans in self.transition():
                if trans.time is None:
                    continue
                enabled.append(trans)
                if trans.time < trans.min_time:
                    step = min(step, trans.min_time - trans.time)
                elif trans.max_time is None:
                    pass
                elif trans.time <= trans.max_time:
                    step = min(step, trans.max_time - trans.time)
                else:
                    raise ConstraintError("%r overtimed" % trans.name)
            for trans in enabled:
                trans.time += step
            return step
    return Transition, Place, PetriNet
