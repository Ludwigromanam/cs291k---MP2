# Copyright 2015 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
# code adapted from https://github.com/tensorflow/tensorflow/blob/r0.8/tensorflow/models/image/cifar10 by Metehan Ozten


from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import random
from six.moves import xrange  # pylint: disable=redefined-builtin
import tensorflow as tf


# Process images of this size. Note that this differs from the original CIFAR
# image size of 32 x 32. If one alters this number, then the entire model
# architecture will change and any model would need to be retrained.
IMAGE_SIZE = 24

# Global constants describing the CIFAR-10 data set.
NUM_CLASSES = 20
NUM_EXAMPLES_PER_EPOCH_FOR_TRAIN = 50000
NUM_EXAMPLES_PER_EPOCH_FOR_VAL = 10000
NUM_EXAMPLES_PER_EPOCH_FOR_EVAL = 10000


def split_train_file(location):
    num_train = NUM_EXAMPLES_PER_EPOCH_FOR_TRAIN*0.9
    num_val = NUM_EXAMPLES_PER_EPOCH_FOR_TRAIN*0.1
    k = [0]*int(num_train)+[1]*int(num_val)
    random.shuffle(k)
    with open(os.path.join(location,'cifar-100-binary', 'train.bin'), 'r') as f:
        train_split_file = open(os.path.join(location,'cifar-100-binary', 'train-split.bin'),'w')
        test_split_file = open(os.path.join(location,'cifar-100-binary', 'val-split.bin'),'w')
        for val in k:
            data = f.read(2+32*32*3)
            if val is 0:
                train_split_file.write(data)
            elif val is 1:
                test_split_file.write(data)
        train_split_file.close()
        test_split_file.close()
    

def read_cifar100(filename_queue):
  """Reads and parses examples from CIFAR10 data files.

  Recommendation: if you want N-way read parallelism, call this function
  N times.  This will give you N independent Readers reading different
  files & positions within those files, which will give better mixing of
  examples.

  Args:
    filename_queue: A queue of strings with the filenames to read from.

  Returns:
    An object representing a single example, with the following fields:
      height: number of rows in the result (32)
      width: number of columns in the result (32)
      depth: number of color channels in the result (3)
      key: a scalar string Tensor describing the filename & record number
        for this example.
      label: an int32 Tensor with the label in the range 0..9.
      uint8image: a [height, width, depth] uint8 Tensor with the image data
  """

  class CIFAR100Record(object): #Creates a place holder object name to act like a dictionary to store data.
    pass
  result = CIFAR100Record()

  # Dimensions of the images in the CIFAR-10 dataset.
  # See http://www.cs.toronto.edu/~kriz/cifar.html for a description of the
  # input format.
  label_bytes = 2 # 2 for CIFAR-100, even though we are only using one label.
  start_at_bytes = 2
  result.height = 32
  result.width = 32
  result.depth = 3
  image_bytes = result.height * result.width * result.depth
  # Every record consists of a label followed by the image, with a
  # fixed number of bytes for each.
  record_bytes = label_bytes + image_bytes #two label bytres

  # Read a record, getting filenames from the filename_queue.  No
  # header or footer in the CIFAR-10 format, so we leave header_bytes
  # and footer_bytes at their default of 0.
  reader = tf.FixedLengthRecordReader(record_bytes=record_bytes)
  result.key, value = reader.read(filename_queue)

  record_bytes = tf.decode_raw(value, tf.uint8)
  result.label = tf.cast(
      tf.slice(record_bytes, [0], [1]), tf.int32) #only snip out the course label

  # The remaining bytes after the label represent the image, which we reshape
  # from [depth * height * width] to [depth, height, width].
  depth_major = tf.reshape(tf.slice(record_bytes, [2], [image_bytes]),
                           [result.depth, result.height, result.width])
  # Convert from [depth, height, width] to [height, width, depth].
  result.uint8image = tf.transpose(depth_major, [1, 2, 0])
  return result


def _generate_image_and_label_batch(image, label, min_queue_examples,
                                    batch_size, shuffle):
  """Construct a queued batch of images and labels.

  Args:
    image: 3-D Tensor of [height, width, 3] of type.float32.
    label: 1-D Tensor of type.int32
    min_queue_examples: int32, minimum number of samples to retain
      in the queue that provides of batches of examples.
    batch_size: Number of images per batch.
    shuffle: boolean indicating whether to use a shuffling queue.

  Returns:
    images: Images. 4D tensor of [batch_size, height, width, 3] size.
    labels: Labels. 1D tensor of [batch_size] size.
  """
  # Create a queue that shuffles the examples, and then
  # read 'batch_size' images + labels from the example queue.
  num_preprocess_threads = 16
  if shuffle:   #In both of these batch subcalls, notice enqueue_many is false
    images, label_batch = tf.train.shuffle_batch(
        [image, label],
        batch_size=batch_size,
        num_threads=num_preprocess_threads,
        capacity=min_queue_examples + 3 * batch_size,
        min_after_dequeue=min_queue_examples)
  else: #Enqueue many is false
    images, label_batch = tf.train.batch(
        [image, label],
        batch_size=batch_size,
        num_threads=num_preprocess_threads,
        capacity=min_queue_examples + 3 * batch_size)


  tf.image_summary('images', images)    # Display the training images in the visualizer.

  return images, tf.reshape(label_batch, [batch_size])


def distorted_inputs(data_dir, batch_size):
  filenames = [os.path.join(os.getcwd(), data_dir,'cifar-100-binary', 'train-split.bin')]
  
  for f in filenames:
    if not tf.gfile.Exists(f):
      raise ValueError('Failed to find file: ' + f)

  # Create a queue that produces the filenames to read.
  filename_queue = tf.train.string_input_producer(filenames)    #This was originally used because the CIFAR10 training had 5 training files

  # Read examples from files in the filename queue.
  read_input = read_cifar100(filename_queue) #pass filename queue into record-reading method
  reshaped_image = tf.cast(read_input.uint8image, tf.float32)

  height = IMAGE_SIZE
  width = IMAGE_SIZE

  # Image processing for training the network. Note the many random
  # distortions applied to the image.

  # Randomly crop a [height, width] section of the image.
  distorted_image = tf.random_crop(reshaped_image, [height, width, 3])

  # Randomly flip the image horizontally.
  distorted_image = tf.image.random_flip_left_right(distorted_image)

  # Because these operations are not commutative, consider randomizing
  # the order their operation.
  distorted_image = tf.image.random_brightness(distorted_image,
                                               max_delta=63)
  distorted_image = tf.image.random_contrast(distorted_image,
                                             lower=0.2, upper=1.8)

  # Subtract off the mean and divide by the variance of the pixels.
  float_image = tf.image.per_image_whitening(distorted_image)

  # Ensure that the random shuffling has good mixing properties.
  min_fraction_of_examples_in_queue = 0.4
  min_queue_examples = int(NUM_EXAMPLES_PER_EPOCH_FOR_TRAIN *
                           min_fraction_of_examples_in_queue)
  print ('Filling queue with %d CIFAR images before starting to train. '
         'This will take a few minutes.' % min_queue_examples)

  images, labels = _generate_image_and_label_batch(float_image, read_input.label, min_queue_examples, batch_size, shuffle = True)
  return images, labels

def inputs(eval_data, data_dir, batch_size):
  if eval_data is "train":
    filenames = [os.path.join(data_dir,'cifar-100-binary', 'train-split.bin')]
    num_examples_per_epoch = int(NUM_EXAMPLES_PER_EPOCH_FOR_TRAIN*0.9)
  elif eval_data is "test":
    filenames = [os.path.join(data_dir,'cifar-100-binary', 'test.bin')]
    num_examples_per_epoch = NUM_EXAMPLES_PER_EPOCH_FOR_EVAL
  elif eval_data is 'val':
    filenames = [os.path.join(data_dir, 'cifar-100-binary','val-split.bin')]
    num_examples_per_epoch = int(NUM_EXAMPLES_PER_EPOCH_FOR_TRAIN*(0.1))
  for f in filenames:
    if not tf.gfile.Exists(f):
      raise ValueError('Failed to find file: ' + f)

  # Create a queue that produces the filenames to read.
  filename_queue = tf.train.string_input_producer(filenames)

  # Read examples from files in the filename queue.
  read_input = read_cifar100(filename_queue)
  reshaped_image = tf.cast(read_input.uint8image, tf.float32)

  height = IMAGE_SIZE
  width = IMAGE_SIZE

  # Image processing for evaluation.
  # Crop the central [height, width] of the image.
  resized_image = tf.image.resize_image_with_crop_or_pad(reshaped_image, width, height)

  # Subtract off the mean and divide by the variance of the pixels.
  float_image = tf.image.per_image_whitening(resized_image)

  # Ensure that the random shuffling has good mixing properties.
  min_fraction_of_examples_in_queue = 0.4
  min_queue_examples = int(num_examples_per_epoch * min_fraction_of_examples_in_queue)
  # Generate a batch of images and labels by building up a queue of examples.
  images, labels = _generate_image_and_label_batch(float_image, read_input.label, min_queue_examples, batch_size, shuffle = False)
  return images, labels
