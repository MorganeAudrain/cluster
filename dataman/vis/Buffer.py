#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Mutable buffer/array that can be shared between multiple processes.
Inspired by https://github.com/belevtsoff/rdaclient.py

* `Buffer`: The buffer
* `datatypes`: supported datatypes
* `BufferHeader`: header structure containing metadata
* `BufferError`: error definitions

"""

from multiprocessing import Array
import ctypes as c
import logging

import numpy as np


class Buffer(object):
    """
    One-dimensional buffer with homogenous elements.

    The buffer can be used simultaneously by multiple processes, because
    both data and metadata are stored in a single sharedctypes byte array.
    First, the buffer object is created and initialized in one of the
    processes. Second, its raw array is shared with others. Third, those
    processes create their own Buffer objects and initialize them so that
    all point to the same shared raw array.
    """

    def __init__(self):
        self.logger = logging.getLogger("Buffer")
        self.__initialized = False

    def __str__(self):
        return self.__buf[:self.bufSize].__str__() + '\n'

    def __getattr__(self, item):
        """Overload to prevent access to the buffer attributes before
        initialization is complete.
        """
        if self.__initialized:
            return object.__getattribute__(self, item)
        else:
            raise BufferError(1)

    # -------------------------------------------------------------------------
    # PROPERTIES

    # read only attributes
    is_initialized = property(lambda self: self.__initialized, None, None,
                              'Indicates whether the buffer is initialized, read only (bool)')
    raw = property(lambda self: self.__raw, None, None,
                   'Raw buffer array, read only (sharedctypes, char)')
    nChannels = property(lambda self: self.__nChannels, None, None,
                         'Dimensionality of array in channels, read only (int)')
    nSamples = property(lambda self: self.__nSamples, None, None,
                        'Dimensionality of array in samples, read only (int)')
    bufSize = property(lambda self: self.__bufSize, None, None,
                       'Buffer size, read only (int)')
    nptype = property(lambda self: self.__nptype, None, None,
                      'The type of the data in the buffer, read only (string)')

    # -------------------------------------------------------------------------

    def initialize(self, nChannels, nSamples, nptype='float32'):
        """Initializes the buffer with a new array.
        """

        # check parameters
        if nChannels < 1 or nSamples < 1:
            self.logger.error('nChannels and nSamples must be a positive integer')
            raise BufferError(1)

        sizeBytes = c.sizeof(BufferHeader) + \
                    nSamples * nChannels * np.dtype(nptype).itemsize
        raw = Array('c', sizeBytes)
        hdr = BufferHeader.from_buffer(raw.get_obj())

        hdr.bufSizeBytes = sizeBytes - c.sizeof(BufferHeader)
        hdr.dataType = datatypes.get_code(nptype)
        hdr.nChannels = nChannels
        hdr.nSamples = nSamples

        self.initialize_from_raw(raw.get_obj())

    def initialize_from_raw(self, raw):
        """Initiates the buffer with the compatible external raw array.
        All the metadata will be read from the header region of the array.
        """
        self.__initialized = True
        hdr = BufferHeader.from_buffer(raw)

        # datatype
        nptype = datatypes.get_type(hdr.dataType)

        bufOffset = c.sizeof(hdr)
        bufFlatSize = hdr.bufSizeBytes / np.dtype(nptype).itemsize

        # create numpy view object pointing to the raw array
        self.__raw = raw
        self.__hdr = hdr
        self.__buf = np.frombuffer(raw, nptype, bufFlatSize, bufOffset) \
            .reshape((-1, hdr.nSamples))

        # helper variables
        self.__nChannels = hdr.nChannels
        self.__bufSize = len(self.__buf)
        self.__nptype = nptype

    def __write_buffer(self, data, start, end=None):
        """Writes data to buffer."""
        # roll array
        # overwrite old section
        if end is None:
            end = start+data.shape[1]
        self.__buf[:, start:end] = data

    def __read_buffer(self, start, end):
        """Reads data from buffer, returning view into numpy array"""
        av_error = self.check_availablility(start, end)
        if not av_error:
            return self.__buf[:, start:end]
        else:
            raise BufferError(av_error)

    def get_data(self, start, end, wprotect=True):
        data = self.__read_buffer(start, end)
        data.setflags(write=not wprotect)
        return data

    def put_data(self, data, start=0):
        datashape = data.shape
        if len(datashape) != 1:
            if (data.shape[1] != self.nChannels):
                raise BufferError(4)
        else:
            datashape = (len(data), 1)
            if self.nChannels != 1:
                raise BufferError(4)

        end = start + len(data)
        self.__write_buffer(data, start, end)

    def check_availablility(self, start, end):
        """Checks whether the requested data samples are available.

        Parameters
        ----------
        start : int
            first sample index (included)
        end : int
            last samples index (excluded)

        Returns
        -------
        0
            if the data is available and already in the buffer
        1
            if the data is available but needs to be read in
        2
            if data is partially unavailable
        3
            if data is completely unavailable


        """
        if start < end:
            return 0
        else:
            return
        # if sampleStart < 0 or sampleEnd <= 0:
        #     return 5
        # if sampleEnd > self.nSamplesWritten:
        #     return 3  # data is not ready
        # if (self.nSamplesWritten - sampleStart) > self.bufSize:
        #     return 2  # data is already erased
        #
        # return 0


class datatypes():
    """A helper class to interpret the type code read from buffer header.
    To add new supported data types, add them to the 'type' dictionary
    """
    types = {0: 'float32',
             1: 'int16'}

    @classmethod
    def get_code(cls, ndtype):
        """Gets buffer type code given numpy datatype

        Parameters
        ----------
        ndtype : string
            numpy datatype (e.g. 'float32')
        """
        idx = cls.types.values().index(ndtype)
        return cls.types.keys()[idx]

    @classmethod
    def get_type(cls, code):
        """Gets numpy data type given a buffer type code

        Parameters
        ----------
        code : int
            type code (e.g. 0)
        """
        return cls.types[code]


class BufferHeader(c.Structure):
    """A ctypes structure describing the buffer header

    Attributes
    ----------
    bufSizeBytes : c_ulong
        size of the buffer in bytes, excluding header and pocket
    pocketSizeBytes : c_ulong
        size of the buffer in bytes
    dataType : c_uint
        typecode of the data stored in the buffer
    nChannels : c_ulong
        sample dimensionality
    nSamplesWritten : c_ulong
        the total number of sample, written after the buffer allocation
    """
    _pack_ = 1
    _fields_ = [('bufSizeBytes', c.c_ulong),
                ('dataType', c.c_uint),
                ('nChannels', c.c_ulong),
                ('nSamples', c.c_ulong)]


class BufferError(Exception):
    """Represents different types of buffer errors"""

    def __init__(self, code):
        """Initializes a BufferError with given error code

        Parameters
        ----------
        code : int
            error code
        """
        self.code = code

    def __str__(self):
        """Prints the error"""
        if self.code == 1:
            return 'buffer is not initialized (error %s)' % repr(self.code)
        elif self.code in [2, 3]:
            return 'unable to get indices (error %s)' % repr(self.code)
        elif self.code == 4:
            return 'writing incompatible data (error %s)' % repr(self.code)
        elif self.code == 5:
            return 'negative index (error %s)' % repr(self.code)
        else:
            return '(error %s)' % repr(self.code)


if __name__ == '__main__':
    buf1 = Buffer()
    buf2 = Buffer()

    buf1.initialize(2, 15)
    buf2.initialize_from_raw(buf1.raw)

    buf1.put_data(np.array([[1, 2], [3, 4]]))
    buf2.put_data(np.array([[5, 6], [7, 8]]), start=2)

    print buf1
    print buf2

    dat = buf2.get_data(0, 4)
    dat[0, 0] = 100

    print buf1
    print buf2