#!/usr/bin/python
#lib3dmm: Parses and writes 3D Movie Maker datafiles
#Copyright (C) 2004-2015 Foone Turing
#
#This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.
#
#This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License along with this program; if not, write to the Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

class lib3dmmException(Exception):
	pass


class LoadError(lib3dmmException):
	pass


class SaveError(Exception):
	pass


class InstallError(Exception):
	pass


class CompressedError(Exception):
	pass
