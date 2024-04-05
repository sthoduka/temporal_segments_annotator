'''
Copyright (c) Santosh Thoduka
This code is licensed under the GPLv3 license, which can be found in the root directory.
'''

from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QGridLayout, QPushButton, QVBoxLayout, QMessageBox
from PyQt5 import QtGui
from PyQt5.QtCore import QTimer
import PyQt5.QtCore as QtCore
import numpy as np
import os
import glob
import json
import cv2
import pdb
import sys
import matplotlib.colors
import argparse

class Annotator(QWidget):
    def __init__(self, args):
        super().__init__()
        self.data_root = args.video_root
        self.annotation_root = args.annotation_root
        self.annotation_file_format = args.annotation_file_format
        self.input_format = args.input_format
        self.input_file_type = args.input_file_type
        if self.input_format == 'video':
            self.trials = sorted(glob.glob(self.data_root + '/*.' + self.input_file_type))
        elif self.input_format == 'image_folder':
            self.trials = sorted(glob.glob(self.data_root + '/*'))
        if len(self.trials) == 0:
            print('No trials found in %s' % self.data_root)
            exit(0)
        self.trial_num = args.trial_num if args.trial_num is not None else 0
        with open('config.json', 'r') as fp:
            self.segment_labels = json.load(fp)["segments"]

        ## https://observablehq.com/@d3/color-schemes  (Categorical Set 1)
        self.colors = ["#e41a1c","#377eb8","#4daf4a","#984ea3","#ff7f00","#ffff33","#a65628","#f781bf","#999999"]
        self.imgs = []

        self.current_img_id = 0
        self.segment_start_id = 0
        self.current_segmentation = []
        self.img_width = 0
        self.selected_cls = 0

        self.setup_ui()

        self.init_images()

        self.fast_timer = QTimer(self)
        self.fast_timer.timeout.connect(self.fast_time_up)
        self.fast_timer.start(30)
        self.running = True
        self.show()

    def keyPressEvent(self, e):
        if e.key() == QtCore.Qt.Key_E:
            self._handle_end_segment()
        elif e.key() == QtCore.Qt.Key_X:
            self._handle_delete_segment()
        elif e.key() == QtCore.Qt.Key_J:
            self.incr_label()
        elif e.key() == QtCore.Qt.Key_K:
            self.decr_label()
        elif e.key() == QtCore.Qt.Key_A:
            self.apply_label()
        elif e.key() == QtCore.Qt.Key_N:
            self._handle_next_trial()
        elif e.key() == QtCore.Qt.Key_B:
            self._handle_next_unlabeled_trial()
        elif e.key() == QtCore.Qt.Key_Space:
            self._handle_play_pause()
        elif e.key() == QtCore.Qt.Key_L:
            self._handle_next_frame()
        elif e.key() == QtCore.Qt.Key_H:
            self._handle_prev_frame()
        elif e.key() == QtCore.Qt.Key_Dollar:
            self._handle_last_frame()
        elif e.key() == QtCore.Qt.Key_0:
            self._handle_first_frame()
        elif e.key() == QtCore.Qt.Key_Q:
            sys.exit()
        elif e.key() == QtCore.Qt.Key_S:
            self._handle_save()

    def incr_label(self):
        self.selected_cls = (self.selected_cls + 1) % len(self.segment_labels)
        for idx, lbl in enumerate(self.cls_labels):
            if idx != self.selected_cls:
                lbl.setStyleSheet("QLabel { background-color : %s; color : black; }" % self.colors[idx] );
            else:
                lbl.setStyleSheet("QLabel { background-color : %s; color : black; font-weight: bold }" % self.colors[idx] );

    def decr_label(self):
        self.selected_cls -=  1
        if self.selected_cls < 0:
            self.selected_cls = len(self.segment_labels) - 1
        for idx, lbl in enumerate(self.cls_labels):
            if idx != self.selected_cls:
                lbl.setStyleSheet("QLabel { background-color : %s; color : black; }" % self.colors[idx] );
            else:
                lbl.setStyleSheet("QLabel { background-color : %s; color : black; font-weight: bold }" % self.colors[idx] );

    def apply_label(self):
        curr_seg_id = -1
        for idx, seg in enumerate(self.current_segmentation):
            if self.current_img_id >= seg["start"] and self.current_img_id <= seg["end"]:
                curr_seg_id = idx
        if curr_seg_id >= 0:
            self.current_segmentation[curr_seg_id]["cls"] = self.segment_labels[self.selected_cls]
            self.update_segmentation_img()

    def _handle_end_segment(self):
        if self.current_img_id <= self.segment_start_id:
            return
        segment = {}
        segment['start'] = self.segment_start_id
        segment['end'] = self.current_img_id
        segment['cls'] = self.segment_labels[self.selected_cls]

        if len(self.current_segmentation) > 0 and segment['start'] < self.current_segmentation[-1]["start"]:
            new_segmentation_list = []
            inserted = False
            for seg in self.current_segmentation:
                if segment["start"] < seg["start"] and not inserted:
                    new_segmentation_list.append(segment)
                    inserted = True
                else:
                    new_segmentation_list.append(seg)
            self.current_segmentation = new_segmentation_list.copy()
        else:
            self.current_segmentation.append(segment)
        self.segment_start_id = self.current_img_id + 1
        self.incr_label()
        self.update_segmentation_img()

    def _handle_delete_segment(self):
        curr_seg_id = -1
        for idx, seg in enumerate(self.current_segmentation):
            if self.current_img_id >= seg["start"] and self.current_img_id <= seg["end"]:
                curr_seg_id = idx
        if curr_seg_id >= 0:
            self.segment_start_id = self.current_segmentation[curr_seg_id]["start"]
            self.current_segmentation = self.current_segmentation[:curr_seg_id]
            self.update_segmentation_img()

    def _handle_next_trial(self):
        self.go_to_next_trial()
        self.running = True

    def _handle_next_unlabeled_trial(self):
        self.go_to_next_unlabeled_trial()
        self.running = True

    def _handle_play_pause(self):
        if self.running:
            self.running = False
        else:
            self.running = True

    def _handle_next_frame(self):
        self.current_img_id += 1
        if self.current_img_id >= len(self.imgs):
            self.current_img_id -= 1
        self.first_img_lbl.setPixmap(QtGui.QPixmap.fromImage(self.imgs[self.current_img_id]))
        self.update_segmentation_img()

    def _handle_prev_frame(self):
        self.current_img_id -= 1
        if self.current_img_id < 0:
            self.current_img_id = 0
        self.first_img_lbl.setPixmap(QtGui.QPixmap.fromImage(self.imgs[self.current_img_id]))
        self.update_segmentation_img()

    def _handle_last_frame(self):
        self.current_img_id = len(self.imgs) - 1
        self.first_img_lbl.setPixmap(QtGui.QPixmap.fromImage(self.imgs[self.current_img_id]))
        self.update_segmentation_img()

    def _handle_first_frame(self):
        self.current_img_id = 0
        self.first_img_lbl.setPixmap(QtGui.QPixmap.fromImage(self.imgs[self.current_img_id]))
        self.update_segmentation_img()

    def show_error(self, msg):
        diag = QMessageBox(self)
        diag.setIcon(QMessageBox.Critical)
        diag.setText("Error")
        diag.setInformativeText(msg)
        diag.setWindowTitle("Error")
        diag.exec_()

    def _handle_save(self):
        if self.input_format == 'video':
            trial_name = os.path.basename(self.trials[self.trial_num]).split('.')[0]
            path = os.path.join(self.annotation_root,  trial_name + '.' + self.annotation_file_format)
        elif self.input_format == 'image_folder':
            trial_name = os.path.basename(self.trials[self.trial_num])
            path = os.path.join(self.annotation_root, trial_name + '.' + self.annotation_file_format)
        # make sure segmentation is contiguous
        prev_end = -1
        for seg in self.current_segmentation:
            if seg["start"] != prev_end + 1:
                self.show_error("Segmentation is not contiguous. Not saving.")
                return
            prev_end = seg["end"]

        if len(self.current_segmentation) == 0:
            self.show_error("No segments defined. Not saving.")
            return
        # make sure segmentation is complete
        if self.current_segmentation[-1]["end"] != len(self.imgs) - 1:
            self.show_error("Segmentation doesn't include complete video. Not saving.")
            return

        if self.annotation_file_format == 'npy':
            segmentation = np.zeros(len(self.imgs), dtype=np.uint8)
            for seg in self.current_segmentation:
                if seg["end"] != len(self.imgs) - 1:
                    segmentation[seg["start"]:seg["end"] + 1] = self.segment_labels.index(seg["cls"])
                else:
                    segmentation[seg["start"]:] = self.segment_labels.index(seg["cls"])

            np.save(path, segmentation)
        else:
            with open(path, 'w') as fp:
                json.dump(self.current_segmentation, fp)

    def _handle_bar_click(self, event):
        pixels_per_frame = float(self.img_width) / len(self.imgs)
        img_id = int(event.x() / pixels_per_frame)
        self.current_img_id = img_id
        if self.current_img_id >= len(self.imgs):
            self.current_img_id = len(self.imgs) - 1
        if self.current_img_id < 0:
            self.current_img_id = 0
        self.first_img_lbl.setPixmap(QtGui.QPixmap.fromImage(self.imgs[self.current_img_id]))
        self.update_segmentation_img()

    def fast_time_up(self):
        if self.running:
            self.current_img_id += 1
            if self.current_img_id >= len(self.imgs):
                self.current_img_id = 0

            self.first_img_lbl.setPixmap(QtGui.QPixmap.fromImage(self.imgs[self.current_img_id]))
            self.update_segmentation_img()

    def setup_ui(self):
        # actual video frame
        self.first_img_lbl = QLabel()
        # segmentation image
        self.second_img_lbl = QLabel()
        self.second_img_lbl.mousePressEvent = self._handle_bar_click
        self.current_episode_lbl = QLabel()
        self.current_seg_lbl = QLabel('test')

        self.frame_num_lbl = QLabel()

        font = QtGui.QFont("Arial", 14, QtGui.QFont.Bold)
        self.current_episode_lbl.setFont(font)
        self.current_episode_lbl.setAutoFillBackground(True)

        self.current_seg_lbl.setFont(font)
        self.current_seg_lbl.setAutoFillBackground(True)

        font = QtGui.QFont("Arial", 20, QtGui.QFont.Bold)
        self.frame_num_lbl.setFont(font)
        self.frame_num_lbl.setAutoFillBackground(True)
        self.frame_num_lbl.setStyleSheet("QLabel {qproperty-alignment: AlignCenter; }")


        # show label types and their colours
        self.cls_labels = []
        for idx, seg in enumerate(self.segment_labels):
            seg_item = QLabel(seg)
            if idx != self.selected_cls:
                seg_item.setStyleSheet("QLabel { background-color : %s; color : black;qproperty-alignment: AlignCenter; }" % self.colors[idx] );
            else:
                seg_item.setStyleSheet("QLabel { background-color : %s; color : black; font-weight: bold;qproperty-alignment: AlignCenter; }" % self.colors[idx] );
            self.cls_labels.append(seg_item)

        self.layout = QGridLayout()
        self.layout.addWidget(self.first_img_lbl, 0, 0, 1, 6)
        self.layout.addWidget(self.second_img_lbl, 1, 0, 1, 6)

        self.layout.addWidget(self.current_seg_lbl, 3, 1, 1, 1)
        self.layout.addWidget(self.frame_num_lbl, 3, 2, 1, 1)
        self.layout.addWidget(self.current_episode_lbl, 3, 3, 1, 1)

        lbl_grid = QVBoxLayout()
        for idx, lbl in enumerate(self.cls_labels):
            lbl_grid.addWidget(lbl)

        self.layout.addLayout(lbl_grid, 2, 0, 2, 1)

        self.setLayout(self.layout)

    def init_images(self):
        if self.input_format == 'video':
            video_path = self.trials[self.trial_num]
            cap = cv2.VideoCapture(video_path)
            self.imgs = []
            frame_num = 0
            prev_frame = None
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                self.img_width = frame.shape[1]
                img = QtGui.QImage(frame.data, frame.shape[1], frame.shape[0], QtGui.QImage.Format_RGB888).rgbSwapped()
                self.imgs.append(img)
                frame_num += 1
            cap.release()
        elif self.input_format == 'image_folder':
            image_paths = sorted(glob.glob(self.trials[self.trial_num] + '/*.' + self.input_file_type))
            self.imgs = []
            frame_num = 0
            prev_frame = None
            for img_path in image_paths:
                frame = cv2.imread(img_path, cv2.IMREAD_COLOR)
                self.img_width = frame.shape[1]
                img = QtGui.QImage(frame.data, frame.shape[1], frame.shape[0], QtGui.QImage.Format_RGB888).rgbSwapped()
                self.imgs.append(img)
                frame_num += 1

        self.current_img_id = 0
        self.segment_start_id = 0
        self.first_img_lbl.setPixmap(QtGui.QPixmap.fromImage(self.imgs[self.current_img_id]))

        self.current_segmentation = []
        trial_name = os.path.basename(self.trials[self.trial_num])
        if self.input_format == 'video':
            trial_name = trial_name.split('.')[0]
        if os.path.exists(os.path.join(self.annotation_root, trial_name + '.' + self.annotation_file_format)):
            if self.annotation_file_format == 'npy':
                segmentation = np.load(os.path.join(os.path.join(self.annotation_root, trial_name + '.npy')))
                current_seg = segmentation[0]
                start = 0
                for frame_id, ss in enumerate(segmentation):
                    if ss == current_seg:
                        continue
                    seg = {}
                    seg["start"] = start
                    seg["end"] = frame_id - 1
                    seg["cls"] = self.segment_labels[current_seg]
                    self.current_segmentation.append(seg)
                    start = frame_id
                    current_seg = ss
                seg = {}
                seg["start"] = start
                seg["end"] = len(segmentation) - 1
                seg["cls"] = self.segment_labels[current_seg]
                self.current_segmentation.append(seg)
            elif self.annotation_file_format == 'json':
                with open(os.path.join(self.annotation_root, trial_name + '.json'), 'r') as fp:
                    self.current_segmentation = json.load(fp)

        self.update_segmentation_img()

        self.current_episode_lbl.setText('%s (%d/%d)' % (trial_name, self.trial_num+1, len(self.trials)))

    def update_segmentation_img(self):
        pixels_per_frame = float(self.img_width) / len(self.imgs)
        seg_img = np.ones((50, self.img_width, 3), dtype=np.uint8) * 255
        start_pixel = 0
        curr_seg_idx = -1
        for idx, seg in enumerate(self.current_segmentation):
            end_pixel = int((seg["end"]) * pixels_per_frame)
            if end_pixel >= self.img_width:
                seg_img[:, start_pixel:] = get_rgb(self.colors[self.segment_labels.index(seg["cls"])])
            else:
                seg_img[:, start_pixel:end_pixel] = get_rgb(self.colors[self.segment_labels.index(seg["cls"])])
            if self.current_img_id >= seg["start"] and self.current_img_id <= seg["end"]:
                curr_seg_idx = idx
            start_pixel = end_pixel

        cursor_img = self.get_cursor_img()
        seg_img = np.concatenate((seg_img, cursor_img), axis=0)

        seg_qimg = QtGui.QImage(seg_img.data, seg_img.shape[1], seg_img.shape[0], QtGui.QImage.Format_RGB888).rgbSwapped()
        self.second_img_lbl.setPixmap(QtGui.QPixmap.fromImage(seg_qimg))

        if curr_seg_idx >= 0:
            display_txt = self.current_segmentation[curr_seg_idx]["cls"]
            self.current_seg_lbl.setText(display_txt)
            self.current_seg_lbl.setStyleSheet("QLabel { background-color : %s; color : black; qproperty-alignment: AlignCenter; }" % self.colors[self.segment_labels.index(display_txt)] );
        else:
            self.current_seg_lbl.setText("")
            self.current_seg_lbl.setStyleSheet("QLabel { background-color : white; color : black; qproperty-alignment: AlignCenter; }" );
        self.frame_num_lbl.setText('%s/%s' % (self.current_img_id +1, len(self.imgs)))

    def get_cursor_img(self):
        pixels_per_frame = float(self.img_width) / len(self.imgs)
        seg_img = np.ones((10, self.img_width, 3), dtype=np.uint8) * 255
        current_pixel = int(pixels_per_frame * self.current_img_id)
        seg_img[:, current_pixel] = [0, 0, 0]
        if current_pixel > 0:
            seg_img[:, current_pixel-1] = [0, 0, 0]

        return seg_img

    def go_to_next_trial(self):
        self.trial_num = self.get_next_trial()
        self.selected_cls = 0
        self.init_images()

    def go_to_next_unlabeled_trial(self):
        prev = -1
        while True:
            self.trial_num = self.get_next_trial()
            trial_name = os.path.basename(self.trials[self.trial_num])
            if self.input_format == 'video':
                trial_name = trial_name.split('.')[0]
            if not os.path.exists(os.path.join(self.annotation_root, trial_name + '.' + self.annotation_file_format)):
                break
            if self.trial_num == prev:
                break
            prev = self.trial_num
        self.selected_cls = 0
        self.init_images()

    def get_next_trial(self):
        orig = self.trial_num
        if (orig < len(self.trials) - 1):
            orig += 1
            return orig
        else:
            return self.trial_num

def get_rgb(hex_str):
    rgb_list = list(matplotlib.colors.to_rgb(hex_str))
    rgb_list = [int(ll * 255) for ll in rgb_list]
    rgb_list.reverse()
    return rgb_list

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--video_root')
    parser.add_argument('-n', '--annotation_root')
    parser.add_argument('-t', '--trial_num')
    parser.add_argument('-a', '--annotation_file_format', default='npy', choices=['npy', 'json'])
    parser.add_argument('-i', '--input_format', default='video', choices=['video', 'image_folder'])
    parser.add_argument('-f', '--input_file_type', default='mp4')
    args = parser.parse_args()
    app = QApplication(sys.argv)
    ex = Annotator(args)
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
