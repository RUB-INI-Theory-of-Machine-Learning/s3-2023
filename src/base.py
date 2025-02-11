#!/usr/bin/env python3
#
# Copyright (C) 2023 Alexandre Jesus <https://adbjesus.com>, Carlos M. Fonseca <cmfonsec@dei.uc.pt>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations

from copy import copy
from typing import TextIO, Optional, Any
from collections.abc import Iterable, Hashable
from dataclasses import dataclass
import logging
import random
import numpy as np

Objective = Any


@dataclass
class Component:
    node: int
    direction: int

    @property
    def cid(self) -> Hashable:
        return self.node, self.direction


@dataclass
class LocalMove:
    i: int
    j: int
    i_dir: int
    j_dir: int


class Solution:
    def __init__(self,
                 problem: Problem,
                 containers: list,
                 directions: list,
                 picked: set,
                 not_picked: set,
                 obj_value: float) -> None:
        self.problem = problem
        self.containers = containers  # list of all containers between depot and treatment plant
        self.directions = directions  # list of directions proportionate to the containers
        self.picked = picked  # list of all picked containers
        self.not_picked = not_picked  # list of all not yet picked containers
        self.obj_value = obj_value

    def output(self) -> str:
        """
        Generate the output string for this solution
        """
        str = ""
        for i in range(len(self.containers)):
            str += f"{self.containers[i] + 1} {self.directions[i]}\n"

        return str.rstrip()

    def copy(self) -> Solution:
        """
        Return a copy of this solution.

        Note: changes to the copy must not affect the original
        solution. However, this does not need to be a deepcopy.
        """
        return self.__class__(
            self.problem,
            copy(self.containers),
            copy(self.directions),
            copy(self.picked),
            copy(self.not_picked),
            self.obj_value
        )

    def is_feasible(self) -> bool:
        """
        Return whether the solution is feasible or not
        """
        # Constraint 1: check if all containers are included in the solution (or picked)
        unique_containers = list(set(self.containers))  # remove duplicates

        if len(unique_containers) != self.problem.n:
            return False
        else:
            # check other constraints
            return True

    def objective(self) -> Optional[Objective]:
        """
        Return the objective value for this solution if defined, otherwise
        should return None
        """
        # case the solution is not completed
        if len(self.not_picked) > 0:
            return None

        # add route from last container to plant and return
        return self.obj_value + self.problem.container_to_plant[self.directions[-1]][self.containers[-1]]

    def lower_bound(self) -> Optional[Objective]:
        """
        Return the lower bound value for this solution if defined,
        otherwise return None
        """
        if len(self.not_picked) == 0:
            return None

        # current obj_value
        obj_value = self.obj_value

        # add the minimal amount of connections to be made (including the plant)
        obj_value += self.get_minimal_connections(self.not_picked)

        return obj_value

    def get_minimal_connections(self, containers) -> int:
        obj_value = 0

        for dest_con in containers:
            options = []
            for dep_con in containers:
                for dir_idx in range(4):
                    if dep_con != dest_con:
                        options.append(self.problem.container_to_container[dir_idx][dep_con][dest_con])

            # add the minimum value
            if len(options) > 0:
                obj_value += min(options)

        # add the route from the last container to the plant
        options = []
        for dep_con in containers:
            for dir_idx in range(2):
                options.append(self.problem.container_to_plant[dir_idx][dep_con])
        obj_value += min(options)

        return obj_value

    def add_moves(self) -> Iterable[Component]:
        """
        Return an iterable (generator, iterator, or iterable object)
        over all components that can be added to the solution
        """
        for container in self.not_picked:
            for direction in range(2):
                yield Component(container, direction)

    def local_moves(self) -> Iterable[LocalMove]:
        """
        Return an iterable (generator, iterator, or iterable object)
        over all local moves that can be applied to the solution
        """
        for idx_1 in range(self.problem.n):
            for idx_2 in range(idx_1, self.problem.n):
                for dir_idx in range(4):
                    if dir_idx == 0:
                        yield LocalMove(idx_1, idx_2, 0, 0)
                    elif dir_idx == 1:
                        yield LocalMove(idx_1, idx_2, 0, 1)
                    elif dir_idx == 2:
                        yield LocalMove(idx_1, idx_2, 1, 0)
                    else:
                        yield LocalMove(idx_1, idx_2, 1, 1)

    def random_local_move(self) -> Optional[LocalMove]:
        """
        Return a random local move that can be applied to the solution.

        Note: repeated calls to this method may return the same
        local move.
        """
        for move in self.random_local_moves_wor():
            return move

    def random_local_moves_wor(self) -> Iterable[LocalMove]:
        """
        Return an iterable (generator, iterator, or iterable object)
        over all local moves (in random order) that can be applied to
        the solution.
        """
        range_1 = list(range(self.problem.n))
        random.shuffle(range_1)
        for idx_1 in range_1:
            range_2 = list(range(idx_1, self.problem.n))
            random.shuffle(range_2)
            for idx_2 in range_2:
                range_dir = list(range(4))
                random.shuffle(range_dir)
                for dir_idx in range_dir:
                    if dir_idx == 0:
                        yield LocalMove(idx_1, idx_2, 0, 0)
                    elif dir_idx == 1:
                        yield LocalMove(idx_1, idx_2, 0, 1)
                    elif dir_idx == 2:
                        yield LocalMove(idx_1, idx_2, 1, 0)
                    else:
                        yield LocalMove(idx_1, idx_2, 1, 1)

    def heuristic_add_move(self) -> Optional[Component]:
        """
        Return the next component to be added based on some heuristic
        rule.
        """
        if len(self.not_picked) == 0:
            return None

        candidates = []
        if len(self.containers) == 0:
            candidates.append(self.problem.depot_to_container[0])
            candidates.append(self.problem.depot_to_container[1])
        else:
            dir_idx_0 = int(str(self.directions[-1]) + str(0), 2)
            dir_idx_1 = int(str(self.directions[-1]) + str(1), 2)
            candidates.append(self.problem.container_to_container[dir_idx_0][self.containers[-1]])
            candidates.append(self.problem.container_to_container[dir_idx_1][self.containers[-1]])

        best_candidate = {"val": max(candidates[0] + candidates[1]), "idx": None, "direction": None}
        for idx in self.not_picked:
            if candidates[0][idx] < best_candidate["val"]:
                best_candidate["val"] = candidates[0][idx]
                best_candidate["idx"] = idx
                best_candidate["direction"] = 0
            if candidates[1][idx] < best_candidate["val"]:
                best_candidate["val"] = candidates[1][idx]
                best_candidate["idx"] = idx
                best_candidate["direction"] = 1

        return Component(best_candidate["idx"], best_candidate["direction"])

    def add(self, component: Component) -> None:
        """
        Add a component to the solution.

        Note: this invalidates any previously generated components and
        local moves.
        """
        if len(self.containers) == 0:
            self.obj_value += self.problem.depot_to_container[component.direction][component.node]
        else:
            self.obj_value += self.connection_cost(Component(self.containers[-1], self.directions[-1]), component)

        self.containers.append(component.node)
        self.directions.append(component.direction)

        self.picked.add(component.node)
        self.not_picked.remove(component.node)

    def connection_cost(self, last_component, new_component):
        if last_component.node == -1:
            return self.problem.depot_to_container[new_component.direction][new_component.node]
        if new_component.node == self.problem.n:
            return self.problem.container_to_plant[last_component.direction][last_component.node]

        # construct the direction index by concat the directions to a binary string a read it in dec
        dir_idx = int(str(last_component.direction) + str(new_component.direction), 2)
        return self.problem.container_to_container[dir_idx][last_component.node][new_component.node]

    def step(self, lmove: LocalMove) -> None:
        """
        Apply a local move to the solution.

        Note: this invalidates any previously generated components and
        local moves.
        """
        tmp = self.containers[lmove.i]
        self.containers[lmove.i] = self.containers[lmove.j]
        self.containers[lmove.j] = tmp

        self.directions[lmove.i] = lmove.i_dir
        self.directions[lmove.j] = lmove.j_dir

    def objective_incr_local(self, lmove: LocalMove) -> Optional[Objective]:
        """
        Return the objective value increment resulting from applying a
        local move. If the objective value is not defined after
        applying the local move return None.
        """
        pc_1 = self.containers[lmove.i - 1] if lmove.i > 0 else -1
        pd_1 = self.directions[lmove.i - 1] if lmove.i > 0 else None
        cc_1 = self.containers[lmove.i]
        cd_1 = self.directions[lmove.i]
        fc_1 = self.containers[lmove.i + 1] if lmove.i < self.problem.n - 1 else self.problem.n
        fd_1 = self.directions[lmove.i + 1] if lmove.i < self.problem.n - 1 else None

        pc_2 = self.containers[lmove.j - 1] if lmove.j > 0 else -1
        pd_2 = self.directions[lmove.j - 1] if lmove.j > 0 else None
        cc_2 = self.containers[lmove.j]
        cd_2 = self.directions[lmove.j]
        fc_2 = self.containers[lmove.j + 1] if lmove.j < self.problem.n - 1 else self.problem.n
        fd_2 = self.directions[lmove.j + 1] if lmove.j < self.problem.n - 1 else None

        obj_value_old = 0
        obj_value_old += self.connection_cost(Component(pc_1, pd_1), Component(cc_1, cd_1))
        obj_value_old += self.connection_cost(Component(cc_1, cd_1), Component(fc_1, fd_1))
        obj_value_old += self.connection_cost(Component(pc_2, pd_2), Component(cc_2, cd_2))
        obj_value_old += self.connection_cost(Component(cc_2, cd_2), Component(fc_2, fd_2))

        obj_value_new = 0
        obj_value_new += self.connection_cost(Component(pc_1, pd_1), Component(cc_2, lmove.j_dir))
        obj_value_new += self.connection_cost(Component(cc_2, lmove.j_dir), Component(fc_1, fd_1))
        obj_value_new += self.connection_cost(Component(pc_2, pd_2), Component(cc_1, lmove.i_dir))
        obj_value_new += self.connection_cost(Component(cc_1, lmove.i_dir), Component(fc_2, fd_2))

        return obj_value_new - obj_value_old

    def lower_bound_incr_add(self, component: Component) -> Optional[Objective]:
        """
        Return the lower bound increment resulting from adding a
        component. If the lower bound is not defined after adding the
        component return None.
        """
        if len(self.not_picked) == 1:
            return 0

        if len(self.containers) == 0:
            new_obj_value = self.problem.depot_to_container[component.direction][component.node]
        else:
            new_obj_value = self.obj_value + self.connection_cost(
                Component(self.containers[-1], self.directions[-1]), component)

        self.not_picked.remove(component.node)
        new_obj_value += self.get_minimal_connections(self.not_picked)
        self.not_picked.add(component.node)

        return new_obj_value - self.lower_bound()

    def perturb(self, ks: int) -> None:
        """
        Perturb the solution in place. The amount of perturbation is
        controlled by the parameter ks (kick strength)
        """
        for i in range(ks):
            self.step(self.random_local_move())

    def components(self) -> Iterable[Component]:
        """
        Returns an iterable to the components of a solution
        """
        for idx in range(self.problem.n):
            yield Component(self.containers[idx], self.directions[idx])


class Problem:
    def __init__(self, n: int, depot_to_container: np.ndarray, container_to_plant: np.ndarray,
                 container_to_container: np.ndarray) -> None:
        self.n = n
        self.depot_to_container = depot_to_container
        self.container_to_plant = container_to_plant
        # index - combination: 0 - 00, 1 - 10, 2 - 11, 3 - 10
        self.container_to_container = container_to_container

    @classmethod
    def from_textio(cls, f: TextIO) -> Problem:
        """
        Create a problem from a text I/O source `f`
        """
        n = int(f.readline())

        depot_to_container = np.empty([2, n])
        container_to_plant = np.empty([2, n])
        # index - combination: 0 - 00, 1 - 01, 2 - 10, 3 - 11
        container_to_container = np.empty([4, n, n])

        for idx in range(1, 5 + 4 * n):
            line = f.readline().strip()  # Remove leading/trailing whitespaces
            elements = [int(x) for x in line.split()]  # Split line by spaces
            if idx == 1:
                depot_to_container[0] = elements
            elif idx == 2:
                depot_to_container[1] = elements
            elif idx == 3:
                container_to_plant[0] = elements
            elif idx == 4:
                container_to_plant[1] = elements
            elif idx < n + 5:
                container_to_container[0][idx - 5] = elements
            elif idx < 2 * n + 5:
                container_to_container[1][idx - n - 5] = elements
            elif idx < 3 * n + 5:
                container_to_container[3][idx - 2 * n - 5] = elements
            else:
                container_to_container[2][idx - 3 * n - 5] = elements

        return cls(n, depot_to_container, container_to_plant, container_to_container)

    def empty_solution(self) -> Solution:
        return Solution(self, [], [], set([]), set(range(self.n)), 0)


if __name__ == '__main__':
    from api.solvers import *
    from time import perf_counter
    import argparse
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument('--log-level',
                        choices=['critical', 'error', 'warning', 'info', 'debug'],
                        default='warning')
    parser.add_argument('--log-file', type=argparse.FileType('w'), default=sys.stderr)
    parser.add_argument('--csearch',
                        choices=['beam', 'grasp', 'greedy', 'heuristic', 'as', 'mmas', 'none'],
                        default='none')
    parser.add_argument('--cbudget', type=float, default=5.0)
    parser.add_argument('--lsearch',
                        choices=['bi', 'fi', 'ils', 'rls', 'sa', 'none'],
                        default='none')
    parser.add_argument('--lbudget', type=float, default=5.0)
    parser.add_argument('--input-file', type=argparse.FileType('r'), default=sys.stdin)
    parser.add_argument('--output-file', type=argparse.FileType('w'), default=sys.stdout)
    args = parser.parse_args()

    logging.basicConfig(stream=args.log_file,
                        level=args.log_level.upper(),
                        format="%(levelname)s;%(asctime)s;%(message)s")

    p = Problem.from_textio(args.input_file)
    s: Optional[Solution] = p.empty_solution()

    start = perf_counter()

    if s is not None:
        if args.csearch == 'heuristic':
            s = heuristic_construction(s)
        elif args.csearch == 'greedy':
            s = greedy_construction(s)
        elif args.csearch == 'beam':
            s = beam_search(s, 10)
        elif args.csearch == 'grasp':
            s = grasp(s, args.cbudget, alpha=0.01)
        elif args.csearch == 'as':
            ants = [s] * 100
            s = ant_system(ants, args.cbudget, beta=5.0, rho=0.5, tau0=1 / 3000.0)
        elif args.csearch == 'mmas':
            ants = [s] * 100
            s = mmas(ants, args.cbudget, beta=5.0, rho=0.02, taumax=1 / 3000.0, globalratio=0.5)

    if s is not None:
        if args.lsearch == 'bi':
            s = best_improvement(s, args.lbudget)
        elif args.lsearch == 'fi':
            s = first_improvement(s, args.lbudget)
        elif args.lsearch == 'ils':
            s = ils(s, args.lbudget)
        elif args.lsearch == 'rls':
            s = rls(s, args.lbudget)
        elif args.lsearch == 'sa':
            s = sa(s, args.lbudget, 30)

    end = perf_counter()

    if s is not None:
        print(s.output(), file=args.output_file)
        if s.objective() is not None:
            logging.info(f"Objective: {s.objective():.3f}")
        else:
            logging.info(f"Objective: None")
    else:
        logging.info(f"Objective: no solution found")

    logging.info(f"Elapsed solving time: {end - start:.4f}")
