import zipfile
import shutil
import uuid
import os


class GerberFile:
    def __init__(self, path: str):
        if not os.path.exists(path):
            raise FileNotFoundError(path)

        self.path: str = path
        self.true_path: None | str = None
        self.has_extracted: bool = False

        self.opened_files: list = []

    def __enter__(self):
        if os.path.isfile(self.path):
            self.has_extracted = True
            self.true_path = str(uuid.uuid4())

            os.makedirs(self.true_path, exist_ok=True)
            with zipfile.ZipFile(self.path, 'r') as zip_ref:
                zip_ref.extractall(self.true_path)

        else:
            self.true_path = self.path
            self.has_extracted = False

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Ensure all files we gave out are closed before deleting / closing
        for file in self.opened_files:
            if not file.closed:
                file.close()

        if self.has_extracted:  # Remove extracted zip
            shutil.rmtree(self.true_path)

        return False  # Ensure errors within loading still show

    def open(self, path, mode):
        """
        Safely opens and returns a file object. Closes automatically when done.
        Or returns None if file does not exist.

        :param path:
        :param mode:
        :return: None | open(path, mode)
        """
        if os.path.exists(os.path.join(self.true_path, path)):
            file = open(os.path.join(self.true_path, path), mode)
            self.opened_files.append(file)
            return file
