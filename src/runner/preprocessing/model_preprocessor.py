from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import tensorflow as tf

import numpy as np
import math
import onnxruntime as rt
import cv2
import json

import importlib
import tensorflow
import tensorflow as tf
from tensorflow import keras

from torchvision import transforms

from .vgg_preprocessor import preprocess_image as vgg_preprocess_image

_R_MEAN = 123.68
_G_MEAN = 116.78
_B_MEAN = 103.94

_SCALE_FACTOR = 0.017

class ModelPreprocessor:

    def __init__(self, data):
        self.data = data


    def preprocess(self, model_name, img_data, preprocessing_enabled):

        lower_model_name = model_name.lower()
        library_or_name = self.data["library"] if self.data["library"] is not None else lower_model_name
        
        np_arr = np.array(img_data)
        if (len(np_arr.shape) == 2):
            np_arr = np.expand_dims(np_arr, axis=(0, 1))
            return np_arr

        if (not preprocessing_enabled):
            img_data = np.expand_dims(np.array(img_data), axis=0)
            if ((self.data["input"][1] == 3 and img_data.shape[1] != 3 or (self.data["input"][1] != 3  and img_data.shape[1] == 3))):
                img_data = np.transpose(img_data, (0, 3, 2, 1))
        
            return img_data

        # If a library conversion is invoked, take the original preprocessing.
        # These libraries have the format of tf_to_keras
        # so I isolate "tf" and then I select preprocessing based on that.
        if("_to_" in library_or_name):
            # Remove library pre/postfix
            if "library_" in library_or_name:
                library_or_name = library_or_name.replace("library_", "")
            
            # Take first before _to_ (source)
            library_or_name = library_or_name.split("_to_")[0].split("_")
            library_or_name = library_or_name[len(library_or_name) - 1]

        if ("keras" in library_or_name):
            img_data = np.array(img_data)
            module_load = importlib.import_module(model_name)

            img_data = np.expand_dims(module_load.preprocess_input(img_data), axis=0)
            # In case of tensor misalignment, apply transpose.
            if(self.data["input"][2] == 3):
                if (img_data.shape[1] == 3):
                    return np.transpose(img_data, (0, 2, 1, 3))
                elif (img_data.shape[3] == 3):
                    return np.transpose(img_data, (0, 2, 3, 1))
        
            if (self.data["input"][1] == 3 and img_data.shape[1] != 3 or (self.data["input"][1] != 3  and img_data.shape[1] == 3)):
                return np.transpose(img_data, (0, 3, 1, 2))

            return img_data

        if("torch" in library_or_name):

            transform = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(self.data["input_dimension"][0]),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])])
    
            img_data = np.expand_dims(transform(img_data), axis=0)
            if ((self.data["input"][1] == 3 and img_data.shape[1] != 3 or (self.data["input"][1] != 3  and img_data.shape[1] == 3))):
                img_data = np.transpose(img_data, (0, 3, 2, 1))
            return img_data

        img_data = np.array(img_data)
        img_data_orig = img_data
        img_data = np.expand_dims(img_data, axis=0)

        if(img_data.shape[1] != 3):
            img_data = np.transpose(img_data, (0, 3, 2, 1))

        preprocessed_value = img_data


        #  -------------------- Tensorflow preprocessing --------------------
        if("googlenet" in lower_model_name):
            preprocessed_value = self.preprocess_googlenet(img_data)
    
        elif ("densenet" in lower_model_name):
            
            # Note: this is the suggested preprocessing for densenet etc.
            preprocessed_value = vgg_preprocess_image(img_data_orig, img_data.shape[2], img_data.shape[2])
            return np.expand_dims(np.array(preprocessed_value), axis=0)

        elif ("mobilenet" in lower_model_name or "shufflenet" in lower_model_name):

            preprocessed_value = self.preprocess_imagenet(preprocessed_value)
    
        elif("inceptionv3" in lower_model_name or "inception_v3" in lower_model_name or "resnet" in lower_model_name):
            preprocessed_value = self.preprocess_inception_v3(preprocessed_value)
        
        if ((self.data["input"][1] == 3 and preprocessed_value.shape[1] != 3 or (self.data["input"][1] != 3  and preprocessed_value.shape[1] == 3))):
            preprocessed_value = np.transpose(preprocessed_value, (0, 3, 2, 1))
    

        if(self.data["input"][2] == 3):
            if (preprocessed_value.shape[1] == 3):
                return np.transpose(preprocessed_value, (0, 2, 1, 3))
            elif (preprocessed_value.shape[3] == 3):
                return np.transpose(preprocessed_value, (0, 2, 3, 1))
        return preprocessed_value

    @staticmethod
    def preprocess_pose(
        image, model_name, input_shape, input_dtype="float32", bbox=None,
        bbox_scale=1.25,
    ):
        """Prepare a pose-model image using the ONNX graph's declared layout."""
        from PIL import Image

        shape = list(input_shape)
        if len(shape) != 4:
            raise ValueError(f"Expected a rank-4 pose input, got {shape}.")
        nhwc = shape[-1] in (1, 3, 4) and shape[1] not in (1, 3, 4)
        height, width = (shape[1], shape[2]) if nhwc else (shape[2], shape[3])
        if not isinstance(height, int) or not isinstance(width, int):
            raise ValueError(f"Dynamic pose input dimensions need an explicit shape: {shape}.")
        channels = shape[-1] if nhwc else shape[1]
        if channels not in (1, 3, 4):
            raise ValueError(
                f"Unsupported pose input channels {channels} in shape {shape}."
            )
        if isinstance(image, (str, bytes)):
            image = Image.open(image)
        image = image.convert({1: "L", 3: "RGB", 4: "RGBA"}[channels])
        original_width, original_height = image.size
        crop = (0.0, 0.0, float(original_width), float(original_height))
        if bbox is not None and len(bbox) >= 4:
            x, y, box_width, box_height = map(float, bbox[:4])
            side = max(box_width, box_height) * float(bbox_scale)
            center_x, center_y = x + box_width / 2, y + box_height / 2
            left, top = center_x - side / 2, center_y - side / 2
            crop = (left, top, side, side)
            image = image.crop((int(left), int(top), int(left + side), int(top + side)))
        image = image.resize((width, height), Image.Resampling.BILINEAR)
        pixels = np.asarray(image)
        lower_name = model_name.lower()
        dtype = np.dtype(input_dtype)
        if dtype.kind == "f":
            pixels = pixels.astype(dtype)
            if "movenet" not in lower_name and "rtmpose" not in lower_name:
                pixels /= 255.0
            elif "rtmpose" in lower_name:
                mean = np.asarray([123.675, 116.28, 103.53], dtype=dtype)
                std = np.asarray([58.395, 57.12, 57.375], dtype=dtype)
                pixels = (pixels - mean) / std
        else:
            pixels = pixels.astype(dtype)
        if not nhwc:
            pixels = np.transpose(pixels, (2, 0, 1))
        transform = {
            "left": crop[0], "top": crop[1],
            "width": crop[2], "height": crop[3],
            "input_width": width, "input_height": height,
        }
        return np.ascontiguousarray(pixels[None, ...]), (height, width), transform

    @staticmethod
    def preprocess_speech(audio, sample_rate, model_name, input_specs, model_dir=None):
        """Prepare mono 16 kHz tensors for the supported speech ONNX families."""
        from math import gcd
        from scipy.signal import resample_poly

        audio = np.asarray(audio)
        if audio.ndim == 2:
            audio = audio.astype(np.float32).mean(axis=1)
        if audio.ndim != 1:
            raise ValueError(f"Expected mono or stereo audio, got {audio.shape}.")
        if np.issubdtype(audio.dtype, np.integer):
            limits = np.iinfo(audio.dtype)
            audio = audio.astype(np.float32) / max(abs(limits.min), limits.max)
        else:
            audio = audio.astype(np.float32)
        if sample_rate != 16000:
            divisor = gcd(int(sample_rate), 16000)
            audio = resample_poly(
                audio, 16000 // divisor, sample_rate // divisor
            ).astype(np.float32)
        audio = np.nan_to_num(audio, copy=False)

        if not input_specs:
            raise ValueError(f"No ONNX input metadata found for {model_name}.")
        model_name = model_name.lower()
        if "whisper" in model_name:
            from transformers import WhisperFeatureExtractor

            extractor = WhisperFeatureExtractor.from_pretrained(str(model_dir))
            features = extractor(
                audio, sampling_rate=16000, return_tensors="np"
            )["input_features"].astype(np.float32)
            return {input_specs[0]["name"]: features}

        if "citrinet" in model_name:
            features = ModelPreprocessor._log_mel_spectrogram(audio)
            expected_shape = input_specs[0].get("shape", [])
            if len(expected_shape) == 3 and (
                expected_shape[1] == 80 or expected_shape[-1] != 80
            ):
                features = features.T
            inputs = {input_specs[0]["name"]: features[None, ...]}
            if len(input_specs) > 1:
                length_dtype = np.dtype(input_specs[1].get("dtype", "int64"))
                inputs[input_specs[1]["name"]] = np.asarray(
                    [features.shape[-1]], dtype=length_dtype
                )
            return inputs

        inputs = {input_specs[0]["name"]: audio[None, :]}
        if len(input_specs) > 1:
            second_input = input_specs[1]
            if "mask" in second_input["name"].lower():
                inputs[second_input["name"]] = np.ones(
                    (1, audio.shape[0]),
                    dtype=np.dtype(second_input.get("dtype", "int64")),
                )
            else:
                inputs[second_input["name"]] = np.asarray(
                    [audio.shape[0]],
                    dtype=np.dtype(second_input.get("dtype", "int64")),
                )
        return inputs

    @staticmethod
    def _log_mel_spectrogram(audio, sample_rate=16000, mel_bins=80):
        from scipy.signal import stft

        frame_length = int(sample_rate * 0.025)
        frame_step = int(sample_rate * 0.010)
        n_fft = 1 << (frame_length - 1).bit_length()
        _, _, spectrum = stft(
            audio, fs=sample_rate, window="hann", nperseg=frame_length,
            noverlap=frame_length - frame_step, nfft=n_fft,
            boundary="zeros", padded=True,
        )
        power = np.abs(spectrum).astype(np.float32) ** 2
        hz_to_mel = lambda hz: 2595.0 * np.log10(1.0 + hz / 700.0)
        mel_to_hz = lambda mel: 700.0 * (10.0 ** (mel / 2595.0) - 1.0)
        points = mel_to_hz(
            np.linspace(hz_to_mel(0), hz_to_mel(sample_rate / 2), mel_bins + 2)
        )
        frequencies = np.linspace(0, sample_rate / 2, power.shape[0])
        filters = np.zeros((mel_bins, power.shape[0]), dtype=np.float32)
        for index in range(mel_bins):
            low, center, high = points[index:index + 3]
            filters[index] = np.maximum(
                0.0,
                np.minimum(
                    (frequencies - low) / max(center - low, 1e-12),
                    (high - frequencies) / max(high - center, 1e-12),
                ),
            )
        return np.log(np.maximum(filters @ power, 1e-10)).T.astype(np.float32)

    def preprocess_inception_v3(self, img): 

        norm_img_data = np.array(img).astype(np.float32)
    
        for i in range(img.shape[1]):
            norm_img_data[0,i,:,:] /= 255.0
            norm_img_data[0,i,:,:] -= 0.5
            norm_img_data[0,i,:,:] *= 2.0

        return norm_img_data

    def preprocess_googlenet(self, img):
        img = np.array(img).astype(np.float32)
        img[0, 0, :, :] -= 123.68
        img[0, 1,:, :] -= 116.779
        img[0, 2,:, :] -= 103.939
        img[0, [0,1,2],:,:] = img[0, [2,1,0],:,:]

        return img  # * 0.017

    def preprocess_imagenet(self, img):
        mean_vec = np.array([0.485, 0.456, 0.406])
        stddev_vec = np.array([0.229, 0.224, 0.225])
        norm_img_data = np.zeros(img.shape).astype('float32')
        for i in range(img.shape[1]):
            norm_img_data[0, i,:,:] = (img[0, i,:,:]/255 - mean_vec[i]) / stddev_vec[i]
        return norm_img_data

    def preprocess_densenet(self, image, output_height, output_width):
        image = tf.squeeze(image, [0])
        if(image.shape[0] == 3):
            image = np.transpose(image, (1, 2, 0))
        
        image = tf.image.resize(image, [output_height, output_width])
        image = tf.image.central_crop(image, central_fraction=1)
        
        image.set_shape([output_height, output_width, 3])

        image = self._mean_image_subtraction(image, [_R_MEAN, _G_MEAN, _B_MEAN])
        return np.expand_dims(image * _SCALE_FACTOR, axis=0)

    def _mean_image_subtraction(self, image, means):

        if image.get_shape().ndims != 3:
            raise ValueError('Input must be of size [height, width, C>0]')
        num_channels = image.get_shape().as_list()[-1]
        if len(means) != num_channels:
            raise ValueError('len(means) must match the number of channels')

        channels = tf.split(axis=2, num_or_size_splits=num_channels, value=image)
        for i in range(num_channels):
            channels[i] -= means[i]
        return tf.concat(axis=2, values=channels)
