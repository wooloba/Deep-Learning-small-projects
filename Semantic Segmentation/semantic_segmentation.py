import tensorflow as tf
import numpy as np
from input_helper import TextureImages
from tensorflow.contrib.layers import flatten


def W_generator(shape):
    mu = 0
    sigma = 0.1

    W = tf.Variable(tf.truncated_normal(shape,mean=mu,stddev=sigma))

    return W

def SemSeg(input_tensor, is_training):
    # TODO: Implement Semantic Segmentation network here
    # Returned logits must be a tensor of size:
    # (None, image_height, image_width, num_classes + 1)
    # 1st dimension is batch dimension
    # image_height and image_width are the height and width of input_tensor
    # last dimension is the softmax dimension. There are 4 texture classes plus 1 background class
    # therefore last dimension will be 5
    # Hint: To make your output tensor has the same height and width with input_tensor,
    # you can use tf.image.resize_bilinear
    print(input_tensor.shape)
    with tf.name_scope("layer1"):
        conv1_W = W_generator([5, 5, 3, 128])
        conv1_b = tf.Variable(tf.zeros(128))
        conv1 = tf.nn.conv2d(input_tensor, conv1_W, strides=[1, 1, 1, 1], padding="VALID") + conv1_b
        conv1 = tf.layers.batch_normalization(conv1, training=True)

        conv1 = tf.nn.relu(conv1)
        conv1 = tf.nn.max_pool(conv1, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding="VALID")

        print('shape of conv1: ', conv1.shape)

    with tf.name_scope("layer2"):
        conv2_W = W_generator([5, 5, 128, 512])
        conv2_b = tf.Variable(tf.zeros(512))
        conv2 = tf.nn.conv2d(conv1, conv2_W, strides=[1, 1, 1, 1], padding='VALID') + conv2_b

        # Batch_Normalization:
        conv2 = tf.layers.batch_normalization(conv2, center=True, scale=True, training=True)

        conv2 = tf.nn.relu(conv2)

        print('shape of conv2: ', conv2.shape)

        conv2 = tf.nn.max_pool(conv2, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='VALID')

    with tf.name_scope("layer3"):
        conv3 = tf.layers.conv2d_transpose(inputs=conv2, filters=128, kernel_size=[5, 5],
                                           strides=[2, 2], padding="VALID", activation=tf.nn.relu)

        print('shape of conv3: ', conv3.shape)

        logits = tf.layers.conv2d_transpose(inputs=conv3, filters=5, kernel_size=[5, 5],
                                            strides=[2, 2], padding="VALID", activation=tf.nn.relu)

        print('shape of conv6: ', logits.shape)
        logits = tf.image.resize_bilinear(images=logits, size=[196, 196])

    return logits


def run():
    # You can tune the hyperparameters here.
    EPOCHS = 10
    BATCH_SIZE = 64
    NUM_ITERS = int(2000 / BATCH_SIZE * EPOCHS)

    train_set = TextureImages('train', batch_size=BATCH_SIZE)
    test_set = TextureImages('test', shuffle=False)

    tf.reset_default_graph()
    x = tf.placeholder(tf.float32, (None, 196, 196, 3))
    y = tf.placeholder(tf.int32, (None, 196, 196, 1))
    one_hot_y = tf.one_hot(y, 5)
    is_training = tf.placeholder(tf.bool, ())

    rate = 0.01
    logits = SemSeg(x, is_training=is_training)
    prediction = tf.argmax(logits, axis=-1)
    cross_entropy = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(logits=logits, labels=one_hot_y))
    loss_operation = cross_entropy
    optimizer = tf.train.AdamOptimizer(learning_rate=rate)
    grads_and_vars = optimizer.compute_gradients(loss_operation, tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES))
    training_operation = optimizer.apply_gradients(grads_and_vars)

    def evaluation(images, true_labels):
        eval_batch_size = 100
        predicted_labels = []
        for start_index in range(0, len(images), eval_batch_size):
            end_index = start_index + eval_batch_size
            batch_x = images[start_index: end_index]
            batch_predicted_labels = sess.run(prediction, feed_dict={x: batch_x, is_training: False})
            predicted_labels += list(batch_predicted_labels)
        predicted_labels = np.vstack(predicted_labels).flatten()
        true_labels = true_labels.flatten()
        accuracy = float((predicted_labels == true_labels).astype(np.int32).sum()) / true_labels.size
        return predicted_labels, accuracy

    sess = tf.Session()
    sess.run(tf.global_variables_initializer())
    print("Training...")
    for i in range(NUM_ITERS):
        batch_x, batch_y = train_set.get_next_batch()
        _ = sess.run(training_operation, feed_dict={x: batch_x, y: batch_y, is_training: True})
        if (i + 1) % 50 == 0 or i == NUM_ITERS - 1:
            _, test_accuracy = evaluation(test_set._images, test_set._masks)
            print("Iter {}: Test Pixel Accuracy = {:.3f}".format(i, test_accuracy))

    print('Evaluating on test set')
    _, test_accuracy = evaluation(test_set._images, test_set._masks)
    print("Test Pixel Accuracy = {:.3f}".format(test_accuracy))
    sess.close()
    return test_accuracy


if __name__ == '__main__':
    run()
