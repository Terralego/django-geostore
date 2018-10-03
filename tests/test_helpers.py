import os

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test.client import RequestFactory
from rest_framework import status

from terracommon.terra.helpers import ChunkIterator, get_media_response


class HelpersTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_chunk_iterator(self):
        chunker = ChunkIterator(iter(range(210)), 20)
        chunks = []
        for chunk in chunker:
            chunks.append(chunk)

        self.assertEqual(11, len(chunks))
        self.assertEqual(10, len(chunks.pop()))

    def test_get_media_response_with_path(self):
        request = self.factory.get('fake/path')

        # Creating a real file
        # In this case, we test if get_media_response return content
        # from a file and so will use open()
        tmp_file = open('/tmp/test.txt', 'wb')
        tmp_file.write(b"ceci n'est pas une pipe")
        tmp_file.seek(0)

        response = get_media_response(
            request,
            {'path': tmp_file.name, 'url': None}  # url none, no accel-redirect
        )

        # Closing & deleting the file since we don't need it anymore
        tmp_file.close()
        os.remove(tmp_file.name)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.content, bytes)
        self.assertEqual(response.content, b"ceci n'est pas une pipe")

    def test_get_media_response_with_file_object(self):
        request = self.factory.get('fake/path')

        tmp_file = SimpleUploadedFile(name='/tmp/file.txt',
                                      content=b'creativity takes courage')

        # Adding fake url, we don't care, we are not testing accel-redirect
        tmp_file.url = None

        response = get_media_response(request, tmp_file)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.content, bytes)
        self.assertEqual(response.content, b'creativity takes courage')
