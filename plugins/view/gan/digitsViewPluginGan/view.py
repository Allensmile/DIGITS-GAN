# Copyright (c) 2016, NVIDIA CORPORATION.  All rights reserved.
from __future__ import absolute_import

import os
import PIL.Image
import PIL.ImageDraw

import numpy as np

import digits
from digits.utils import subclass, override
from digits.extensions.view.interface import VisualizationInterface
from .forms import ConfigForm


CONFIG_TEMPLATE = "templates/config_template.html"
HEADER_TEMPLATE = "templates/header_template.html"
VIEW_TEMPLATE = "templates/view_template.html"


@subclass
class Visualization(VisualizationInterface):
    """
    A visualization extension to display the output of a GAN
    """

    def __init__(self, dataset, **kwargs):
        """
        Init
        """
        # memorize view template for later use
        extension_dir = os.path.dirname(os.path.abspath(__file__))
        self.view_template = open(
            os.path.join(extension_dir, VIEW_TEMPLATE), "r").read()

        self.normalize = True
        self.col_count = 10
        self.row_count = 10

        # view options
        self.task_id = kwargs['gan_view_task_id']

    @staticmethod
    def get_config_form():
        return ConfigForm()

    @staticmethod
    def get_config_template(form):
        """
        parameters:
        - form: form returned by get_config_form(). This may be populated
        with values if the job was cloned
        returns:
        - (template, context) tuple
          - template is a Jinja template to use for rendering config options
          - context is a dictionary of context variables to use for rendering
          the form
        """
        extension_dir = os.path.dirname(os.path.abspath(__file__))
        template = open(
            os.path.join(extension_dir, CONFIG_TEMPLATE), "r").read()
        context = {'form': form}
        return (template, context)

    @override
    def get_header_template(self):
        """
        Implements get_header_template() method from view extension interface
        """
        extension_dir = os.path.dirname(os.path.abspath(__file__))
        template = open(
            os.path.join(extension_dir, HEADER_TEMPLATE), "r").read()
        return template, {'cols': range(self.col_count),
                          'rows': range(self.row_count)}

    @staticmethod
    def get_id():
        return "image-gan"

    @staticmethod
    def get_title():
        return "GAN"

    def get_image_html(self, image):
        # assume 8-bit
        if self.normalize:
            image -= image.min()
            if image.max() > 0:
                image /= image.max()
                image *= 255
        else:
            # clip
            image = image.clip(0, 255)

        # convert to uint8
        image = image.astype('uint8')

        # convert to PIL image
        channels = image.shape[2]
        if channels == 1:
            # drop channel axis
            image = PIL.Image.fromarray(image[:, :, 0])
        elif channels == 3:
            image = PIL.Image.fromarray(image)
        else:
            raise ValueError("Unhandled number of channels: %d" % channels)

        image_html = digits.utils.image.embed_image_html(image)

        return image_html

    @override
    def get_view_template(self, data):
        """
        parameters:
        - data: data returned by process_data()
        returns:
        - (template, context) tuple
          - template is a Jinja template to use for rendering config
          options
          - context is a dictionary of context variables to use for
          rendering the form
        """
        context = {'key': data['key']}
        if self.task_id == 'grid':
            context.update({'task_id': self.task_id,
                            'col_id': data['col_id'],
                            'row_id': data['row_id'],
                            'image': data['image']})
        elif self.task_id in ['celeba_encoder', 'mnist_encoder']:
            context.update({'task_id': 'encoder',
                            'z': data['z'],
                            'image_input': data['image_input'],
                            'image_output': data['image_output']})
        else:
            raise ValueError("Unknown task: %s" % self.task_id)
        return self.view_template, context

    @override
    def process_data(self, input_id, input_data, output_data):
        """
        Process one inference and return data to visualize
        """
        data = output_data[output_data.keys()[0]].astype('float32')

        if self.task_id == 'grid':
            col_id = int(input_id) // self.col_count
            row_id = int(input_id) % self.col_count
            image_html = self.get_image_html(data)

            return {'image': image_html,
                    'col_id': col_id,
                    'row_id': row_id,
                    'key': input_id}
        elif self.task_id == 'mnist_encoder':
            self.z_dim = 100
            z = data[:self.z_dim]
            image = data[self.z_dim:].reshape(28, 28)
            input_data = input_data.astype('float32')
            input_data = input_data[:, :, np.newaxis]
            image = image[:, :, np.newaxis]
            image_input_html = self.get_image_html(input_data)
            image_output_html = self.get_image_html(image)
            return {'z': z,
                    'image_input': image_input_html,
                    'image_output': image_output_html,
                    'key': input_id}
        elif self.task_id == 'celeba_encoder':
            self.z_dim = 100
            z = data[:self.z_dim]
            image = data[self.z_dim:].reshape(64, 64, 3)
            input_data = input_data.astype('float32')
            image_input_html = self.get_image_html(input_data)
            image_output_html = self.get_image_html(image)
            return {'z': z,
                    'image_input': image_input_html,
                    'image_output': image_output_html,
                    'key': input_id}
        else:
            raise ValueError("Unknown task: %s" % self.task_id)