class ChunkIterator:

    def __init__(self, iterator, chunksize):
        self.iterator = iterator
        self.chunksize = chunksize

    def __iter__(self):
        return self
    
    def __next__(self):
        try:
            chunk = []
            for i in range(self.chunksize):
                chunk.append(next(self.iterator))
        finally:
            if chunk:
                return chunk
            else:
                raise StopIteration

    def next(self):
        return self.__next__()
