import tkinter as tk
import automaton
import threading
import json
from configparser import ConfigParser
from itertools import product
from math import ceil
from collections import defaultdict

with open('language.json', encoding = 'utf-8') as file:
	raw = json.load(file)
	languages = defaultdict((lambda: defaultdict(str)), {i: defaultdict(str, j) for i, j in raw.items()})

config = ConfigParser()
config.read('setting.ini')

grid_size = int(config['Graph Setting']['grid size']) #px

vertical_offset = int(config['Graph Setting']['vertical offset'])
horizon_offset = int(config['Graph Setting']['horizon offset'])

word = languages[config['Localize']['language']]

noop = automaton.noop

class App():
	_close: bool = False
	_master: tk.Misc #tk.Misc is the common base of tk.Tk and tk.Toplevel, and having method winfo_toplevel
	_width: int
	_height: int
	_now_mainloop = None
	_simulating: bool = False
	def __init__(self, master: tk.Misc = None):
		if master is None:
			master = tk.Tk()
		self._master = master
		self._master.winfo_toplevel().protocol('WM_DELETE_WINDOW', self.onclosing)
		while not self._close:
			self.input_size_generator()
			if not self._close:
				self.life_game()
	@property
	def master(self):
		return self._master
	@staticmethod
	def title(widget, s: str):
		if isinstance(widget, tk.Wm):
			widget.title(s)
	@staticmethod
	def _draw_cross_for_fix(atm, cell_frame, i, j):
		cell_frame.create_line(j * grid_size + horizon_offset, i * grid_size + vertical_offset
			, (j + 1) * grid_size - 1 + horizon_offset, (i + 1) * grid_size - 1 + vertical_offset
			, tags = ('fix', f'fix{i}-{j}'), fill = '#fff' if atm[i, j] else '#000', width = ceil(grid_size / 8))
		cell_frame.create_line((j + 1) * grid_size - 1 + horizon_offset, i * grid_size + vertical_offset
			, j * grid_size + horizon_offset, (i + 1) * grid_size - 1 + vertical_offset
			, tags = ('fix', f'fix{i}-{j}'), fill = '#fff' if atm[i, j] else '#000', width = ceil(grid_size / 8))
	def _grid_button_bind(self, atm: automaton.CellAutomata, cell_frame: tk.Canvas, cell_id):
		def sol(event, *args):
			print(event)
			if self._simulating:
				return
			i, j = (event.y - vertical_offset) // grid_size, (event.x - horizon_offset) // grid_size
			if i >= atm.height or j >= atm.width or i < 0 or j < 0:
				return
			if event.num == 1:
				if atm.getfix((i, j)):
					return
				sol = not atm[i, j]
				cell_frame.itemconfigure(cell_id[i][j], fill = '#000' if sol else '#fff')
				atm.setvalue((i, j), sol)
			elif event.num == 3:
				atm.switchfix((i, j))
				sol = atm.getfix((i, j))
				if sol:
					self._draw_cross_for_fix(atm, cell_frame, i, j)
				else:
					cell_frame.delete(f'fix{i}-{j}')
		return sol
	@staticmethod
	def _grid_sim_change(atm: automaton.CellAutomata, cell_frame: tk.Canvas, cell_id):
		def sol(width, height, origin, result, fixed, **kwargs):
			for i, j in product(range(height), range(width)):
				if origin[i][j] is not result[i][j]:
					cell_frame.itemconfigure(cell_id[i][j], fill = '#000' if result[i][j] else '#fff')
		return sol
	def input_size_generator(self):
		input_size_widget = tk.Frame(self._master)
		self.title(input_size_widget.master, word['key in size'])

		a, b = tk.Frame(input_size_widget), tk.Frame(input_size_widget)
		a_text, b_text = tk.Label(a, text = word['width']), tk.Label(b, text = word['height'])
		hint_text = tk.Label(input_size_widget, text = word['please key in width and height'])
		var_width = tk.StringVar(input_size_widget)
		var_height = tk.StringVar(input_size_widget)
		input_width = tk.Entry(a, width = 4, textvariable = var_width)
		input_height = tk.Entry(b, width = 4, textvariable = var_height)
		var_width.set('5')
		var_height.set('5')
		var_msg = tk.StringVar(input_size_widget)
		error_msg = tk.Label(input_size_widget, textvariable = var_msg, foreground = '#f00')
		accept_button = tk.Button(input_size_widget, text = word['accept'], command = input_size_widget.quit)

		input_size_widget.pack(expand = True)
		hint_text.pack(side = 'top')
		a.pack(pady = 10), b.pack(pady = 10)
		a_text.pack(side = 'left'), b_text.pack(side = 'left')
		input_width.pack(side = 'right')
		input_height.pack(side = 'right')
		error_msg.pack()
		accept_button.pack()

		while not self._close:
			self.mainloop(input_size_widget)
			if not self._close:
				fail = True
				for entry in (input_width, input_height):
					s = entry.get()
					if not s.isdigit():
						entry.focus()
						var_msg.set(word['please key in a number!'])
						break
					elif int(s) < 3:
						entry.focus()
						var_msg.set(word['please key in a number at least 3!'])
						break
					else:
						fail = False
				if not fail:
					self._width, self._height = int(var_width.get()), int(var_height.get())
					break #do not return, do destroy
			print(233)
		input_size_widget.destroy()
	def life_game(self):
		if self._width is None or self._height is None:
			return
		self._simulating = False
		width, height = self._width, self._height
		simulation = None
		Id = None
		atm_backup = None
		mutex = threading.Lock()

		life_game_widget = tk.Frame(self._master)
		self.title(life_game_widget.master, f"{word['cellular automaton']} {self._width}x{self._height}")

		atm = automaton.CellAutomata(width = width, height = height)

		cell_frame = tk.Canvas(life_game_widget, bg = '#fff', width = width * grid_size, height = height * grid_size)
		cell_id = [[cell_frame.create_rectangle(j * grid_size + horizon_offset, i * grid_size + vertical_offset, (j + 1) * grid_size + horizon_offset, (i + 1) * grid_size + vertical_offset, fill = '#fff', state = tk.DISABLED, width = 0, tags = 'cell')
					for j in range(width)] for i in range(height)]

		cycle_frame = tk.Frame(life_game_widget)
		round_msg = tk.Label(cycle_frame, text = word['round number'])
		round_number = tk.Label(cycle_frame, text = '1')
		beforecycle_msg = tk.Label(cycle_frame, text = word['rounds before cycle'])
		beforecycle_number = tk.Label(cycle_frame, text = word['unknown'])
		cycle_msg = tk.Label(cycle_frame, text = word['cycling length'])
		cycle_number = tk.Label(cycle_frame, text = word['unknown'])

		continuous_frame = tk.Frame(life_game_widget)
		continuous_way = ['vertical_cycle', 'horizontal_cycle']
		continuous_var = {way: tk.IntVar(continuous_frame) for way in continuous_way}
		continuous_option = {way: tk.Checkbutton(continuous_frame, text = word[way], variable = continuous_var[way]) for way in continuous_way}

		rule_frame = tk.Frame(life_game_widget)
		rule_hint = tk.Label(rule_frame, text = word['detect direction'])
		direct = ['up', 'down', 'left', 'right', 'left_top', 'left_bottom', 'right_top', 'right_bottom']
		direct_var = {d: tk.IntVar(rule_frame) for d in direct}
		direct_option = {d: tk.Checkbutton(rule_frame, text = word[d], variable = direct_var[d]) for d in direct}
		for o in direct_option.values():
			o.select()

		number_frame = tk.Frame(life_game_widget)
		number_kind = ['keep', 'born']
		number_hint = {kind: tk.Label(number_frame, text = word[kind]) for kind in number_kind}
		number_var = {kind: [tk.IntVar(number_frame) for i in range(9)] for kind in number_kind}
		number_option = {kind: [tk.Checkbutton(number_frame, text = str(i), variable = number_var[kind][i]) for i in range(9)] for kind in number_kind}
		number_option['keep'][2].select()
		number_option['keep'][3].select()
		number_option['born'][3].select()

		flag_msg = tk.StringVar(life_game_widget) #invisible
		bottombutton = tk.Frame(life_game_widget)
		back = tk.Button(bottombutton, text = word['reset size'], state = tk.NORMAL
			, command = lambda: (flag_msg.set('resize'), life_game_widget.quit()))
		clear = tk.Button(bottombutton, text = word['clear'], state = tk.NORMAL
			, command = lambda: (flag_msg.set('clear'), life_game_widget.quit()))
		stop_return = tk.Button(bottombutton, text = word['stop and go back'], state = tk.DISABLED
			, command = lambda: (flag_msg.set('stop_return'), life_game_widget.quit()))
		startstop = tk.Button(bottombutton, text = word['start']
			, command = lambda: (flag_msg.set('start'), life_game_widget.quit()))

		scale_frame = tk.Frame(life_game_widget)
		freq_var = tk.IntVar(scale_frame)
		freq_times = tk.IntVar(scale_frame)
		freq_times.set(1)
		scale = tk.Scale(scale_frame, from_ = 1, to = 20, orient = tk.HORIZONTAL, variable = freq_var)
		freq_times_option = tk.Radiobutton(scale_frame, text = word['times per second'], variable = freq_times, value = 1)
		freq_divide_option = tk.Radiobutton(scale_frame, text = word['seconds per time'], variable = freq_times, value = 0)
		freq_times_option.select()

		wait_time = lambda: 1000 // freq_var.get() if freq_times.get() else 1000 * freq_var.get()

		life_game_widget.pack(expand = True)
		cell_frame.pack()
		cycle_frame.pack()
		round_msg.grid(row = 0, column = 0)
		round_number.grid(row = 0, column = 1)
		beforecycle_msg.grid(row = 1, column = 0)
		beforecycle_number.grid(row = 1, column = 1)
		cycle_msg.grid(row = 2, column = 0)
		cycle_number.grid(row = 2, column = 1)
		continuous_frame.pack()
		for i, way in enumerate(continuous_way):
			continuous_option[way].grid(row = 0, column = i)
		rule_frame.pack()
		rule_hint.grid(row = 0, column = 0)
		for i, d in enumerate(direct, 1):
			direct_option[d].grid(row = 0, column = i)
		number_frame.pack()
		for i, kind in enumerate(number_kind):
			number_hint[kind].grid(row = i, column = 0)
			for j, n in enumerate(number_option[kind], 1):
				n.grid(row = i, column = j)
		bottombutton.pack()
		back.grid(row = 0, column = 0, padx = 10)
		clear.grid(row = 0, column = 1, padx = 10)
		stop_return.grid(row = 0, column = 2, padx = 10)
		startstop.grid(row = 0, column = 3, padx = 10)
		scale_frame.pack()
		scale.grid(row = 0, column = 0, rowspan = 2)
		freq_times_option.grid(row = 0, column = 1)
		freq_divide_option.grid(row = 1, column = 1)

		def _used_in_tk_after():
			with mutex:
				round_count, loop_cycle, round_before_cycle = next(simulation)
				round_number['text'] = str(round_count)
				cycle_number['text'] = word['unknown'] if loop_cycle is None else str(loop_cycle)
				beforecycle_number['text'] = word['unknown'] if loop_cycle is None else str(round_before_cycle)
				nonlocal Id
				Id = life_game_widget.after(ms = wait_time(), func = _used_in_tk_after)

		def _state_switch(start: bool):
			to_be_disabled = tk.DISABLED if start else tk.NORMAL
			to_be_normal = tk.NORMAL if start else tk.DISABLED
			for o in continuous_option.values():
				o['state'] = to_be_disabled
			for d in direct_option.values():
				d['state'] = to_be_disabled
			for kind in number_kind:
				for o in number_option[kind]:
					o['state'] = to_be_disabled
			back['state'] = to_be_disabled
			clear['state'] = to_be_disabled
			stop_return['state'] = to_be_normal

		while not self._close:
			flag_msg.set('')
			if not self._simulating:
				cell_frame.bind('<Button>', self._grid_button_bind(atm, cell_frame, cell_id))
			self.mainloop(life_game_widget)
			cell_frame.bind('<Button>', noop)
			msg = flag_msg.get()
			print(msg)
			if msg == 'resize':
				break
			elif msg == 'clear':
				cell_frame.itemconfigure('cell', fill = '#fff')
				cell_frame.delete('fix')
				atm.setallfix(value = False)
				atm.setback()
			elif msg == 'start':
				self._simulating = True
				_state_switch(True)
				atm_backup = atm.copy()
				simulation = atm.simulate(
					automaton.CellAutomata.fgenerator(
						**{d: direct_var[d].get() == 1 for d in direct},
						**{way: continuous_var[way].get() == 1 for way in continuous_way},
						accept_keep_number = {i for i, n in enumerate(number_var['keep']) if n.get() == 1},
						accept_born_number = {i for i, n in enumerate(number_var['born']) if n.get() == 1}
					)
					, change_to_status = self._grid_sim_change(atm, cell_frame, cell_id), pick_loop = True)
				startstop['text'] = word['stop']
				startstop['command'] = lambda: (flag_msg.set('stop'), life_game_widget.quit())
				cell_frame.delete('fix')
				Id = life_game_widget.after(ms = wait_time(), func = _used_in_tk_after)
			elif msg == 'stop' or msg == 'stop_return':
				with mutex:
					life_game_widget.after_cancel(Id)
				self._simulating = False
				_state_switch(False)
				round_number['text'] = '1'
				cycle_number['text'] = word['unknown']
				beforecycle_number['text'] = word['unknown']
				startstop['text'] = word['start']
				startstop['command'] = lambda: (flag_msg.set('start'), life_game_widget.quit())
				if msg == 'stop_return':
					atm = atm_backup
					for i, j in product(range(height), range(width)):
						cell_frame.itemconfigure(cell_id[i][j], fill = '#000' if atm[i, j] else '#fff')
				for i, j in product(range(height), range(width)):
					if atm.getfix((i, j)):
						self._draw_cross_for_fix(atm, cell_frame, i, j)
		life_game_widget.destroy()
	def mainloop(self, widget):
		self._now_mainloop = widget
		widget.mainloop()
		self._now_mainloop = None
	def onclosing(self):
		self._close = True
		if self._now_mainloop is not None:
			self._now_mainloop.quit()

if __name__ == '__main__':
	App()