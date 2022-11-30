# File: main.py
import sys
import json
import pprint
import enum

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Enum, Text
#from sqlalchemy.sql import select

from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton
from PySide6.QtCore import QFile, QIODevice
from PySide6.QtGui import QPixmap

IMAGE_DIR = '/usr/local/bgnn/joel_pred_mask_images'
ERR_IMAGE_DIR = '/usr/local/bgnn/inhs_validation'

with open('./check_labels.json') as f:
    metadata = json.load(f)
#filename = None
#curr_metadata = None
#window = None

LEV_DIST_CUTOFF = 3

# engine = create_engine('sqlite:///label_checking.sqlite')#, echo=True)
engine = create_engine(
    'sqlite:///ieee-cas-label-checking.sqlite')  # , echo=True)
conn = engine.connect()
Session = sessionmaker(bind=engine)
session = Session()

Base = declarative_base()


class ErrTypes(enum.Enum):
    ocr = 1
    tilt = 2
    synonym = 3
    complex_name_format = 4
    inadmissibility = 5
    true_error = 6
    ok = 7


class Record(Base):
    __tablename__ = 'results'

    id = Column(Integer, primary_key=True)
    filename = Column(String)
    sci_name = Column(String)
    err_type = Column('err_type', Enum(ErrTypes))
    description = Column(Text)

    def __repr__(self):
        return f'User {self.name}'


Base.metadata.create_all(engine)


def load_next():
    fname_gen = get_filename()
    global filename
    filename = fname_gen.__next__()
    print(filename)
    global curr_metadata
    curr_metadata = metadata[filename]
    if 'errored' not in curr_metadata.keys():
        pixmap = QPixmap('{}/check_labels_prediction_{}.png'
                         .format(IMAGE_DIR, filename))
        window.label_text.setPlainText(curr_metadata['tag_text'])
        del curr_metadata['tag_text']
    else:
        pixmap = QPixmap('{}/{}'
                         .format(ERR_IMAGE_DIR, filename))
        window.label_text.clear()
        window.metadata.clear()
    window.metadata.setPlainText(pprint.pformat(curr_metadata))
    window.picture_frame.setPixmap(pixmap)
    window.scientific_name.clear()
    window.further_descr.clear()
    print()
    done = session.query(Record).count()
    window.sys_status.setPlainText(('Overall Total: {}\nTotal to Check: {}' +
                                    '\n\tErrored: {}\n\tDidn\'t Match: {}' +
                                    '\n\tLev Dist > {}: {}\nDone: {}' +
                                    '\nRemaining: {}')
                                   .format(total, count, errored, didnt_match, LEV_DIST_CUTOFF,
                                           lev_dist_above, done, count - done))


def classification_button_callback(err_type, metadata_correct=True):
    def callback():
        if not metadata_correct:
            name = window.scientific_name.toPlainText()
        else:
            try:
                name = curr_metadata['metadata_name'].capitalize()
            except KeyError:
                name = "Errored out, must run program to debug"
        name = Record(filename=filename, sci_name=name,
                      err_type=err_type, description=window.further_descr.toPlainText())
        session.add(name)
        session.commit()
        load_next()
    return callback


def descr_append_callback(descr_append_text):
    def callback():
        window.further_descr.setPlainText(window.further_descr.toPlainText() + descr_append_text + ' ')
    return callback


def get_filename():
    for filename in metadata.keys():
        if 'errored' in metadata[filename].keys() or\
                ((not metadata[filename]['matched_metadata'])
                 or metadata[filename]['lev_dist'] > LEV_DIST_CUTOFF):

            #s = select(Base)
            #s = select(Record).filter_by(filename=filename)
            result = session.query(Record).filter_by(filename=filename).all()
            if not result:
                yield filename


def main():
    app = QApplication(sys.argv)

    ui_file_name = "picture_viewer.ui"
    ui_file = QFile(ui_file_name)
    if not ui_file.open(QIODevice.ReadOnly):
        print(f"Cannot open {ui_file_name}: {ui_file.errorString()}")
        sys.exit(-1)
    loader = QUiLoader()
    global window
    window = loader.load(ui_file)
    ui_file.close()
    if not window:
        print(loader.errorString())
        sys.exit(-1)

    global count
    global errored
    global didnt_match
    global lev_dist_above
    count, errored, didnt_match, lev_dist_above = 0, 0, 0, 0
    for key in metadata.keys():
        if 'errored' in metadata[key].keys():
            errored += 1
            count += 1
        elif not metadata[key]['matched_metadata']:
            didnt_match += 1
            count += 1
        elif metadata[key]['lev_dist'] > LEV_DIST_CUTOFF:
            lev_dist_above += 1
            count += 1
    global total
    total = len(metadata.keys())

    load_next()

    window.ocr.clicked.connect(classification_button_callback(ErrTypes.ocr))
    window.ruler_noise.clicked.connect(descr_append_callback("Ruler noise"))
    window.handwritten_noise.clicked.connect(descr_append_callback("Handwritten noise"))
    window.tilt.clicked.connect(classification_button_callback(ErrTypes.tilt))
    window.synonym.clicked.connect(classification_button_callback(ErrTypes.synonym))
    window.complex_name_format.clicked.connect(classification_button_callback(ErrTypes.complex_name_format))
    window.inadmissibility.clicked.connect(classification_button_callback(ErrTypes.inadmissibility))
    window.true_error.clicked.connect(classification_button_callback(ErrTypes.true_error))
    window.ok.clicked.connect(classification_button_callback(ErrTypes.ok))

    window.show()
    exit_code = app.exec()
    session.close()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
