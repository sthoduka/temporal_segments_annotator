A tool to annotate temporal segments in untrimmed videos with activity classes. This can be used, for example, to label videos used for [temporal action segmentation](https://arxiv.org/abs/2210.10352). The resultant annotation is a class label for each frame of the video.

![screenshot](docs/screenshot.jpg)

## Requirements
* OpenCV
* PyQt5
* Matplotlib

## Usage
```
usage: annotate_segments.py [-h] [-r VIDEO_ROOT] [-n ANNOTATION_ROOT] [-t TRIAL_NUM] [-a {npy,json}] [-i {video,image_folder}]
                            [-f INPUT_FILE_TYPE]

optional arguments:
  -h, --help            show this help message and exit
  -r VIDEO_ROOT, --video_root VIDEO_ROOT
  -n ANNOTATION_ROOT, --annotation_root ANNOTATION_ROOT
  -t TRIAL_NUM, --trial_num TRIAL_NUM
  -a {npy,json}, --annotation_file_format {npy,json}
  -i {video,image_folder}, --input_format {video,image_folder}
  -f INPUT_FILE_TYPE, --input_file_type INPUT_FILE_TYPE {mp4, jpg}
```

Class labels can be defined in [config.json](config.json).

## Keyboard shortcuts

```
j           increment label selection
k           decrement label selection
e           end current segment using selected label

a           apply current label to current segment
x           delete current segment

<spacebar>  play/pause
l           next frame
h           previous frame
$           last frame
0           first frame

n           next trial
b           next unlabelled trial

q           quit
s           save
```

## Similar tools
The following tools can also be used to label video segments, but have other functionalities in addition:

* [VGG Image Annotator (VIA)](https://www.robots.ox.ac.uk/~vgg/software/via/)
* [Behavioral Observation Research Interactive Software (BORIS)](http://www.boris.unito.it/)
* [DLC2Action](https://github.com/amathislab/dlc2action_annotation)
