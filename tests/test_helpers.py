from django.test import TestCase

from terracommon.terra.helpers import ChunkIterator


class HelpersTestCase(TestCase):

    def test_chunk_iterator(self):
        chunker = ChunkIterator(iter(range(210)), 20)
        chunks = []
        for chunk in chunker:
            chunks.append(chunk)

        self.assertEqual(11, len(chunks))
        self.assertEqual(10, len(chunks.pop()))
