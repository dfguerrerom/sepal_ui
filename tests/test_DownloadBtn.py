import unittest

import ipyvuetify as v

from sepal_ui import sepalwidgets as sw
from sepal_ui.scripts.utils import create_download_link

class TestDownloadBtn(unittest.TestCase):
    
    def test_init(self):
        
        #default init
        txt = 'toto'
        btn = sw.DownloadBtn(txt)
        start = "/api/files/download?path="
        
        self.assertIsInstance(btn, sw.DownloadBtn)
        self.assertEqual(btn.children[0].children[0], 'mdi-download')
        self.assertEqual(btn.children[1], txt)
        self.assertIn(start, btn.href)
        self.assertIn('#', btn.href)
        
        #exhaustive 
        link = 'toto/ici'
        btn = sw.DownloadBtn(txt, link)
        self.assertIn(link, btn.href)
        
        #absolute link  
        absolute_link = "http://www.fao.org/home/en/"
        btn = sw.DownloadBtn(txt, absolute_link)
        self.assertEqual(absolute_link, btn.href)
        
        return
    
    def test_create_download_link(self):
        
        #relative link 
        start = "/api/files/download?path="
        relative_link = 'toto/ici'
        
        path = create_download_link(relative_link)
        
        self.assertIn(start, path)
        self.assertIn(relative_link, path)
        
        return 
        
if __name__ == '__main__':
    unittest.main()