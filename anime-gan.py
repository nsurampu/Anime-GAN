import PIL
import matplotlib.pyplot as plt
from tqdm import tqdm_notebook

import keras
from keras.models import Sequential
from keras.layers import Dense, Activation, Flatten, Reshape
from keras.layers import Conv2D, Conv2DTranspose, UpSampling2D
from keras.layers import LeakyReLU, Dropout
from keras.layers import BatchNormalization
from keras.optimizers import Adam, RMSprop
from keras.preprocessing.image import load_img ,img_to_array

import numpy as np
import os

from multiprocessing.pool import ThreadPool
from multiprocessing import cpu_count

class ANIME_GAN:

    def __init__(self):
        self.path = '/home/naren/Downloads/anime-face-dataset'
        self.latent_dim = 64
        self.height = 64
        self.width = 64
        self.channels = 3
        self.iterations = 15000
        self.batch_size = 32
        self.dataset = None

    def generator_model(self):
        generator_input = keras.Input(shape = (self.latent_dim,))

        x = Dense(128 * 32 * 32)(generator_input)
        x = LeakyReLU()(x)
        x = Reshape((32,32,128))(x)

        x = Conv2D(256, 5, padding='same')(x)
        x = LeakyReLU()(x)

        x = Conv2DTranspose(256, 4, strides = 2, padding = 'same')(x)
        x = LeakyReLU()(x)

        x = Conv2D(256, 5, padding='same')(x)
        x = LeakyReLU()(x)
        x = Conv2D(256, 5, padding='same')(x)
        x = LeakyReLU()(x)

        x = Conv2D(self.channels, 7, activation = 'tanh', padding = 'same')(x)
        generator = keras.models.Model(generator_input, x)
        generator.summary()

        return generator

    def discriminator_model(self):
        discriminator_input = keras.Input(shape = (self.height, self.width, self.channels))
        x = Conv2D(128, 3)(discriminator_input)
        x = LeakyReLU(0.2)(x)
        x = Conv2D(128, 4, strides = 2)(x)
        x = LeakyReLU(0.2)(x)
        x = Conv2D(128, 4, strides = 2)(x)
        x = LeakyReLU()(x)
        x = Conv2D(128, 4, strides = 2)(x)
        x = LeakyReLU()(x)

        x = Flatten()(x)

        x = Dropout(0.4)(x)

        x = Dense(1, activation = 'sigmoid')(x)

        discriminator = keras.models.Model(discriminator_input, x)
        discriminator.summary()

        return discriminator

    def train_gan(self, generator, discriminator):
        discriminator.trainable = False

        gan_input = keras.Input(shape=(self.latent_dim,))
        gan_output = discriminator(generator(gan_input))
        gan = keras.models.Model(gan_input, gan_output)

        gan_optimizer = keras.optimizers.RMSprop(lr = 0.0004, clipvalue = 1.0, decay = 1e-8)
        gan.compile(optimizer = gan_optimizer, loss = 'binary_crossentropy')

        discriminator_optimizer = keras.optimizers.RMSprop(
          lr = 0.0008,
          clipvalue = 1.0,
          decay = 1e-8
        )
        discriminator.compile(optimizer = discriminator_optimizer,
        loss='binary_crossentropy')

        start = 0
        x_train = []

        for image in self.dataset:
            img_path = self.path + "/" + image
            img = PIL.Image.open(img_path)
            img_arr = np.array(img)
            x_train.append(img_arr)

        x_train = np.array(x_train)

        for step in range(self.iterations):
          print("##### STEP " + str(step) + " #####")
          random_latent_vectors = np.random.normal(size = (self.batch_size, self.latent_dim))
          generated_images = generator.predict(random_latent_vectors)
          stop = start + self.batch_size
          real_images = x_train[start: stop]
          # print(type(generated_images), type(real_images))
          # print(generated_images[0])
          # print(generated_images[0].shape)
          combined_images = np.concatenate([generated_images, real_images])
          labels = np.concatenate([np.ones((self.batch_size,1)),
                                            np.zeros((self.batch_size, 1))])
          labels += 0.05 * np.random.random(labels.shape)

          d_loss = discriminator.train_on_batch(combined_images, labels)

          random_latent_vectors = np.random.normal(size=(self.batch_size,
                                                         self.latent_dim))
          misleading_targets = np.zeros((self.batch_size, 1))
          a_loss = gan.train_on_batch(random_latent_vectors,
                                      misleading_targets)
          start += self.batch_size

          if start > len(x_train) - self.batch_size:
            start = 0

          # Print the loss and also plot the faces generated by generator
          if step % 50 == 0 or step % 50 != 0:
            print('discriminator loss:', d_loss)
            print('advesarial loss:', a_loss)
            fig, axes = plt.subplots(2, 2)
            fig.set_size_inches(2,2)
            count = 0
            for i in range(2):
              for j in range(2):
                axes[i, j].imshow(np.resize(generated_images[count], (64,64)))
                axes[i, j].axis('off')
                count += 1
            plt.savefig("STEP" + str(step) + ".png", dpi=600)
            print("Figure at step saved")

          # We save every 100 steps
          if step % 100 == 0:
            gan.save_weights('dcgan.h5')

          print('discriminator loss:', d_loss)
          print('advesarial loss:', a_loss)

if __name__ == "__main__":
    pool = ThreadPool(processes=cpu_count())

    anime_gan = ANIME_GAN()
    anime_gan.dataset = os.listdir(anime_gan.path)
    generator = anime_gan.generator_model()
    discriminator= anime_gan.discriminator_model()

    (pool.apply_async(anime_gan.train_gan(generator, discriminator))).get()
