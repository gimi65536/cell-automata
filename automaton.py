from itertools import count, product
from typing import Optional, Set, Tuple
from collections import OrderedDict

_default_length = 5
_default_init = False
default_str = lambda sl: ''.join(('●' if i else '○') for i in sl)

noop = lambda *args, **kwargs: None

class CellAutomata():
	_width: int = _default_length
	_height: int = _default_length
	_l: list
	_fix: list

	#simulate is an iterator so simulating will not block
	#however, the drawback is that the deletion of an iterator or the creation of other iterators cannot be detected
	#so, it is the user's work to prevent wild situation
	#_simulating: bool = False
	def __init__(self, width: int = _default_length, height: int = _default_length, init = _default_init):
		self._width = width
		self._height = height
		self._l = [[init for j in range(self._width)] for i in range(self._height)]
		self._fix = [[False for j in range(self._width)] for i in range(self._height)]
	def setback(self, init = _default_init, override_fix = False):
		for i, j in product(range(self._height), range(self._width)):
			if not override_fix and self._fix[i][j]:
				continue
			self._l[i][j] = init
	def setallfix(self, value: bool):
		for i, j in product(range(self._height), range(self._width)):
			self._fix[i][j] = value
	def setfix(self, key: Tuple[int, int], value: bool):
		i, j = key
		self._fix[i][j] = value
	def getfix(self, key: Tuple[int, int]):
		i, j = key
		return self._fix[i][j]
	def switchfix(self, key: Tuple[int, int]):
		i, j = key
		self._fix[i][j] = not self._fix[i][j]
	def setvalue(self, key: Tuple[int, int], value, override_fix = False):
		i, j = key
		if not override_fix and self._fix[i][j]:
			return
		self._l[i][j] = value
	def __getitem__(self, key: Tuple[int, int]):
		try:
			i, j = key
			return self._l[i][j]
		except:
			return None
	@property
	def width(self):
		return self._width
	@property
	def height(self):
		return self._height
	def copy(self):
		sol = self.__class__(self._width, self._height, False)
		for i, j in product(range(self._height), range(self._width)):
			sol._l[i][j] = self._l[i][j] #shallow copy
			sol._fix[i][j] = self._fix[i][j] #shallow but already deep due to bool
		return sol
	def simulate(self, func, rnd: Optional[int] = None, change_to_state = noop, change_to_status = noop, pick_loop = False):
		if change_to_state is None:
			change_to_state = noop
		#if self._simulating:
		#	return
		ite = None
		if rnd is None:
			ite = count(0)
		else:
			ite = range(rnd)
		#self._simulating = True
		round_count = 1
		loop_set, loop_cycle, round_before_cycle = OrderedDict(), None, None
		if pick_loop:
			s = tuple([tuple([self._l[i][j] for j in range(self._width)]) for i in range(self._height)])
			loop_set[s] = ''
		for _ in ite:
			#if not self._simulating:
			#	break
			l = [[self._l[i][j] for j in range(self._width)] for i in range(self._height)]
			for i, j in product(range(self._height), range(self._width)):
				if not self._fix[i][j]:
					l[i][j] = func(self, i, j)
				change_to_state(row = i, column = j, origin = self._l[i][j], result = l[i][j], fixed = self._fix[i][j])
			if change_to_status is not None:
				change_to_status(width = self._width, height = self._height, origin = self._l.copy(), result = l.copy(), fixed = self._fix.copy())
			self._l = l
			if pick_loop and loop_cycle is None:
				s = tuple([tuple([self._l[i][j] for j in range(self._width)]) for i in range(self._height)])
				if s not in loop_set:
					loop_set[s] = ''
				else:
					index = list(loop_set.keys()).index(s)
					loop_cycle = len(loop_set) - index
					round_before_cycle = round_count - loop_cycle
			round_count = round_count + 1
			msg = (yield round_count, loop_cycle, round_before_cycle)
			if msg is not None:
				break
		#self.stop_simulate()
	#def stop_simulate(self):
	#	self._simulating = False
	def __str__(self):
		return self.string(str)
	def string(self, func):
		return '\n'.join(func(i) for i in self._l)
	@staticmethod
	def fgenerator(*, four_direct: Optional[bool] = None
					, up: bool = True, down: bool = True, left: bool = True, right: bool = True
					, left_top: bool = False, left_bottom: bool = False, right_top: bool = False, right_bottom: bool = False
					, horizontal_cycle: bool = False, vertical_cycle: bool = False
					, accept_keep_number: Set[int] = {2, 3}, accept_born_number: Set[int] = {3}):
		if four_direct is True:
			up, down, left, right, left_top, left_bottom, right_top, right_bottom = True, True, True, True, False, False, False, False
		elif four_direct is False:
			up, down, left, right, left_top, left_bottom, right_top, right_bottom = True, True, True, True, True, True, True, True
		table = [(-1, 0), (+1, 0), (0, -1), (0, +1), (-1, -1), (+1, -1), (-1, +1), (+1, +1)]
		def func(automaton: CellAutomata, row: int, column: int):
			counter, width, height = 0, automaton.width, automaton.height
			for direct, (row_delta, column_delta) in zip((up, down, left, right, left_top, left_bottom, right_top, right_bottom), table):
				if not direct:
					continue
				row_after, column_after = row + row_delta, column + column_delta
				if horizontal_cycle:
					column_after = column_after % width
				if vertical_cycle:
					row_after = row_after % height
				if column_after < 0 or column_after >= width or row_after < 0 or row_after >= height:
					continue
				if automaton[row_after, column_after]:
					counter = counter + 1
			#print(f'({row}, {column}) = counter')
			return (counter in accept_keep_number) if automaton[row, column] else (counter in accept_born_number)
		return func

if __name__ == '__main__':
	c = CellAutomata(width = 5, height = 5)
	c.setvalue((2, 2), True)
	c.setvalue((1, 1), True)
	c.setvalue((1, 3), True)
	c.setvalue((3, 1), True)
	c.setvalue((3, 3), True)
	i = c.simulate(CellAutomata.fgenerator(four_direct = False, accept_keep_number = {2, 3, 4, 5, 6}, accept_born_number = {2, 3, 4, 5, 6}))
	from time import sleep
	while True:
		print(c.string(default_str))
		print()
		sleep(0.5)
		next(i)