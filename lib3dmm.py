#!/usr/bin/python
#lib3dmm: Parses and writes 3D Movie Maker datafiles
#Copyright (C) 2004-2015 Foone Turing
#
#This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.
#
#This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License along with this program; if not, write to the Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

from struct import unpack,calcsize,pack
from error import LoadError,SaveError
from sources import *
import cStringIO

def sread(file,struct):
	size=calcsize(struct)
#	print 'Reading %s:%i' % (struct,size)
	res=unpack(struct,file.read(size))
	if len(res)==1:
		return res[0]
	else:
		return res


class Quad(object):
	MAIN_QUAD_FLAG = 2
	COMPRESSED_FLAG = 4

	def __init__(self,type,id=0,mode=0,string=0):
		self.type=type
		self.id=id
		self.string=string
		self.mode=mode
		self.source=MemorySource('')
		self.references=[]

	def setData(self,string):
		self.source=MemorySource(string)

	def addReference(self,otherquad,refid):
		self.references.append((refid,otherquad))

	def getLength(self):
		return self.source.get_length()

	def write(self,fop):
		self.source.write(fop)

	def getNumReferences(self):
		return len(self.references)

	def isCompressed(self):
		return bool(self.mode&Quad.COMPRESSED_FLAG)


class c3dmmFileOut(object):

	def __init__(self):
		self.quads=[]
		self.sig='CHMP'
		self.unks=(5,4)
		self.magic=(1,0,3,3)

	def addQuad(self,quad):
		self.quads.append(quad)

	def getData(self):
		strio=cStringIO.StringIO()
		self.saveToFile(strio)
		return strio.getvalue()

	def save(self,filename):
		fop=open(filename,'wb')
		self.saveToFile(fop)
		fop.close()

	def saveToFile(self,fop):
		offset=128
		quadaddys=[]
		sortedquads=self.makeSortedQuads()
		for quad in sortedquads:
			length=quad.getLength()
			quadaddys.append((offset,quad,length))
			offset+=length
		print '---'
		for quad in sortedquads:
			print quad.type
		print '+++'
		for off,quad,length in quadaddys:
			print off,quad.type,length
		print '---',offset

		indexoffset=offset
		index=self.makeIndex(quadaddys)
		indexlength=len(index)
		total_length=indexoffset+indexlength
		header=self.makeHeader(total_length,indexoffset,indexlength)
		fop.write(header)
		for quad in sortedquads:
			quad.write(fop)
		fop.write(index)

	def makeHeader(self,length,indexoffset,indexlength):
		header=pack('<8s 2H 4B 4L 96s', 'CHN2' + self.sig[::-1],self.unks[0],self.unks[1],self.magic[0],self.magic[1],self.magic[2],self.magic[3],length,indexoffset,indexlength,length,'')
		return header

	def makeIndex(self,quadaddys):
		index=''
		quadentries=[]
		quadmap={}
		quadslength=0
		for rquad in self.quads:
			found=False
			for offset,quad,length in quadaddys:
				if not found and quad is rquad:
					qe=self.makeQuadEntry(offset,quad)
					quadentries.append((quadslength,qe))
					quadmap[(quad.type,quad.id)]=(quadslength,qe)
					quadslength+=len(qe)
					found=True
			if not found:
				raise SaveError('missing quad!')
		index+=pack('<4B 2L 2l',self.magic[0],self.magic[1],self.magic[2],self.magic[3],len(self.quads),quadslength,-1,20)
		postindex=''
		for offset,quadentry in quadentries:
			index+=quadentry
		for off,quad,length in quadaddys:
			offset,quadentry=quadmap[(quad.type,quad.id)]
			postindex+=pack('<2L',offset,len(quadentry))
		index+=postindex
		return index

	def makeQuadEntry(self,offset,quad):
		qe=pack('<4s 2L B',quad.type[::-1],quad.id,offset,quad.mode)
		qe+=pack('<L',quad.getLength())[0:3] # 24 bit numbers ROCK MY COCK OFF
		qe+=pack('<2H',quad.getNumReferences(),self.getReferenceCount(quad))
		for refid,oquad in quad.references:
			qe+=pack('<4s 2L',oquad.type[::-1],oquad.id,refid)
		return qe

	def getReferenceCount(self,mainquad):
		count=0
		for quad in self.quads:
			for refid,oquad in quad.references:
				if oquad is mainquad:
					count+=1
		return count

	def makeSortedQuads(self):
		sorted=self.quads[:]
		sorted.sort(self.cmpquad)
		return sorted

	def cmpquad(self,a,b):
		return cmp(a.type,b.type)


class c3dmmFile(object):

	def __init__(self,filename=None,cache=False):
		self.cache=cache
		if filename is not None:
			self.load(filename)
		else:
			self.reset()

	def reset(self):
		self.filename=None
		self.id='        '
		self.version=(0,0)
		self.file_length=self.index_offset=0
		self.index_length=self.quad_count=self.quads_length=self_quad_start=0
		self.quad_index=[]
		self.quads=[]

	def load(self,filename):
		self.reset()
		self.filename=filename
		fop=open(filename,'rb') # you know my feelings on this issue.
		self.id=sread(fop,'<8s')
		self.version=sread(fop,'<HH')
		marker=sread(fop,'<4B')
		if not marker in [(1,0,3,3),(1,0,5,5)]:
			raise LoadError('Bad/missing marker at %i'%fop.tell())
		self.file_length,self.index_offset=sread(fop,'<2L')
		self.index_length,dummy=sread(fop,'<2L')
		fop.seek(self.index_offset)
		marker=sread(fop,'<4B')
		if not marker in [(1,0,3,3),(1,0,5,5)]:
			raise LoadError('Bad/missing marker at %i'%fop.tell())
		self.quad_count,self.quads_length=sread(fop,'<LL')
		unk=sread(fop,'<ll')
		if unk!=(-1,20):
			print 'unk in indexheader is not -1,20? value: %i,%i' % unk
		self.quad_start=self.index_offset+20
		self.load_quad_index(fop)
		self.load_quads(fop)

	def load_quad_index(self,fop):
		fop.seek(self.quad_start+self.quads_length)
		self.quad_index=[]
		for i in range(self.quad_count):
			self.quad_index.append(sread(fop,'<2L')) 

	def load_quads(self,fop):
		self.quads=[]
		for i in range(self.quad_count):
			cquad={}
			offset,length=self.quad_index[i]
			fop.seek(self.quad_start+offset)
			type=sread(fop,'<4s')[::-1]
			id,section_offset=sread(fop,'<2L')
			mode=sread(fop,'<B')
			section_length=unpack('<L',fop.read(3)+'\0')[0]
			references,references_to_this_quad=sread(fop,'<2H')
#			print type,id,section_offset,mode,section_length,references,references_to_this_quad
			length_of_references=12*references
			cquad['reference_count']=references
			cquad['references_to_this_quad_count']=references_to_this_quad
			cquad['references']=[]
			cquad['type']=type
			cquad['id']=id
			cquad['mode']=mode
			cquad['section_offset']=section_offset
			cquad['section_length']=section_length
			cquad['source']=FileSource(self.filename,section_offset,section_length)
			if self.cache:
				cquad['source']=cquad['source'].make_memory_source()
			for j in range(references):
				ref_type=sread(fop,'<4s')[::-1]
				ref_id,ref_ref_id=sread(fop,'<2L')
#				print 'Ref: %s %i %i' % (ref_type,ref_id,ref_ref_id)
				cref={}
				cref['type']=ref_type
				cref['id']=ref_id
				cref['ref_id']=ref_ref_id
				cquad['references'].append(cref)
			if length_of_references+20!=length: # We have a string
				marker=sread(fop,'<2B')
				if marker==(3,3): # ASCII
					length=sread(fop,'<B')
					str=sread(fop,'<%is' % length)
					cquad['string']=str
				elif marker==(5,5): # unicode!
					length=sread(fop,'<B')
					ustr=u''
					for c in range(length):
						char=sread(fop,'!H')
						ustr+=unichr(char)
					cquad['string']=ustr
				else:
					raise LoadError('Expected string marker 3,3 or 5,5 but got %i,%i!' %marker)
			else:
				cquad['string']=None
			self.quads.append(cquad)
		pass

	def save(self,filename):
		data_size=0
		for quad in self.quads:
			data_size+=quad['source'].get_length()
		print data_size

	def dump(self):
		print 'id:',self.id
		print 'version:',self.version
		print 'file length:',self.file_length
		print 'index offset:',self.index_offset
		print 'index length:',self.index_length
		print 'number of quads:',self.quad_count
		print 'quads length:',self.quads_length

		for quad in self.quads:
			if quad['references_to_this_quad_count']==0:
				after=''
				if quad['string'] is not None:
					after='(%s)' % quad['string']
				if len(quad['references'])==0:
					print '* %s %s' % (quad['type'],after)
				else:
					print '+ %s %s' % (quad['type'],after)
					self.dump_quad(quad)

	def dump_quad(self,quad,level=1):
		sep='  ' * level
		for ref in quad['references']:
			subquad=self.find_quad(ref['type'],ref['id'])
			if subquad is not None:
				after=''
				if subquad['string'] is not None:
					after='(%s)' % subquad['string']
				if len(subquad['references'])==0:
					print '%s* %s %s' % (sep,ref['type'],after)
				else:
					print '%s+ %s %s' % (sep,ref['type'],after)
					self.dump_quad(subquad,level+1)
			else:
				print '%s* %s !' % (sep,ref['type'])

	def find_quad(self,type,id):
		for quad in self.quads:
			if quad['type']==type and quad['id']==id:
				return quad

if __name__=='__main__':
	import sys
	f=c3dmmFile(sys.argv[1])
	f.dump()
	for quad in f.quads:
		print quad['type'],quad.isCompressed()