# -*- coding: utf-8 -*-
from snakes.plugins import plugin
from snakes.typing import *
from snakes.data import *


@plugin("snakes.nets")
def extend(module):
    class Transition(module.Transition):
        def __init__(self, name, guard=None, **kwargs):
            self.time = None                            # elapsed time
            self.min_time = kwargs.pop('min_time', 0.0)   # min duration
            self.max_time = kwargs.pop('max_time', None)  # max duration
            module.Transition.__init__(self, name, guard, **kwargs)

        def enabled(self, binding, **kwargs):
            if kwargs.pop("untimed", False):
                return module.Transition.enabled(self, binding)
            elif self.time is None:
                return False
            elif self.max_time is None:
                return (self.time >= self.min_time) \
                    and module.Transition.enabled(self, binding)
            else:
                return (self.min_time <= self.time <= self.max_time) \
                    and module.Transition.enabled(self, binding)

    class Place (module.Place):
        def __init__(self, name, tokens=[], check=None):
            self.name = name
            self.tokens = MultiSet()
            if check is None:
                self._check = tAll
            else:
                self._check = check
            self.check(iterate(tokens))
            self.tokens.add(iterate(tokens))

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

    class PetriNet (module.PetriNet):
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
                    raise ConstraintError, '%s overtimed' % repr(trans.name)
            for trans in enabled:
                trans.time += step
            return step

    return Transition, Place, PetriNet