#!/usr/bin/env python3

import os
from tempfile import NamedTemporaryFile
from abc import ABC, abstractmethod

class FileFilter(ABC):
	"""
	An abstract class that filters the content of a file. It works by passing an
	input and output stream to an abstract function. If the abstract function
	return true, the output of the output stream is then copied into the
	origional file.
	"""
	def __init__(self, filename, makefile=False):
		self.filename = filename
		if makefile:
			if not os.path.exists(filename):
				with open(filename, 'w+'):
					pass

	@abstractmethod
	def filter_stream(self, in_stream, out_stream):
		pass

	def run(self):
		dirpath = os.path.dirname(self.filename)
		retval = False
		if not os.path.exists(self.filename):
			with open(self.filename, 'w+') as f:
				pass
		with open(self.filename) as source, NamedTemporaryFile('w', dir=dirpath, delete=False) as outfile:
			retval = self.filter_stream(source, outfile)
		if retval != False:
			with open(outfile.name) as inflow, open(self.filename, 'w+') as outflow:
				for line in inflow:
					outflow.write(line)
		os.remove(outfile.name)
		return retval != False

class UpdateSection(FileFilter):
	"""
	A FileFilter that updates the section of a file that exists between two set
	lines. If the set lines are not found, they are added to the end of the file
	along with the new content.
	"""
	def __init__(self, filename, start_text, end_text, new_content):
		self.start_text = start_text.strip()
		self.end_text = end_text.strip()
		self.new_content = new_content.strip()
		super().__init__(filename, True)

	def filter_stream(self, in_stream, out_stream):
		skip = False
		updated = False
		for line in in_stream:
			stripped_line = line.strip()
			if stripped_line == self.start_text:
				out_stream.write(line)
				out_stream.write(self.new_content + '\n')
				skip = True
				updated = True
			elif stripped_line == self.end_text:
				skip = False
				out_stream.write(line)
			elif not skip:
				out_stream.write(line)
		if not updated:
			out_stream.write(self.start_text + '\n')
			out_stream.write(self.new_content + '\n')
			out_stream.write(self.end_text + '\n')
		return True

class FilterIfExists(FileFilter):
	"""A FileFilter that skips running if the source file does not exist."""
	def run(self):
		if os.path.exists(self.filename):
			return super().run()
		return False

class AppendUnique(FileFilter):
	"""
	Append a line of text to a file but only if the file does not already
	contain a matching line.
	"""
	def __init__(self, filename, new_content, ignore_trim=False, ignore_case=False):
		self.new_content = new_content
		self.ignore_trim = ignore_trim
		self.ignore_case = ignore_case
		super().__init__(filename, True)

	def get_compare_text(self, text):
		if self.ignore_case:
			text = text.lower()
		if self.ignore_trim:
			text = text.strip()
		else:
			while text.endswith('\n') or text.endswith('\r'):
				text = text[:-1]
		return text

	def filter_stream(self, in_stream, out_stream):
		found = 0
		test_content = self.get_compare_text(self.new_content)
		for line in in_stream:
			compare_line = self.get_compare_text(line)
			if compare_line == test_content:
				found += 1
			out_stream.write(line)
		if found == 0:
			out_stream.write(self.new_content + '\n')
			return True
		return False

class RemoveExact(AppendUnique):
	"""Remove a line from a file."""
	def filter_stream(self, in_stream, out_stream):
		found = 0
		test_content = self.get_compare_text(self.new_content)
		for line in in_stream:
			if self.get_compare_text(line) == test_content:
				found += 1
			else:
				out_stream.write(line)
		return found > 0

class RemoveRegex(FileFilter):
	"""Remove a line from a file that matches a given regular expression."""
	def __init__(self, filename, compiled_regex):
		self.re = compiled_regex
		super().__init__(filename, True)

	def filter_stream(self, in_stream, out_stream):
		found = 0
		for line in in_stream:
			if self.re.match(line):
				found += 1
			else:
				out_stream.write(line)
		return found > 0

class ReplaceRegex(FileFilter):
	"""Replace lines in a file that match a given regular expression."""
	def __init__(self, filename, compiled_regex, replacement, limit=-1):
		self.re = compiled_regex
		self.replacement = replacement
		self.limit = limit
		super().__init__(filename, True)

	def filter_stream(self, in_stream, out_stream):
		found = 0
		for line in in_stream:
			if self.re.match(line) and (self.limit == -1 or self.limit > found):
				found += 1
				out_stream.write(self.replacement)
			else:
				out_stream.write(line)
		return found > 0
