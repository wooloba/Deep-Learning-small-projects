import numpy as np
import tensorflow as tf
import data_loader
from Nets import net
from tensorflow.contrib.layers import flatten


def add_gradient_summaries(grads_and_vars):
    for grad, var in grads_and_vars:
        if grad is not None:
            tf.summary.histogram(var.op.name + "/gradient", grad)


def train(x_train, y_train,x_valid,y_valid,train_bbox,valid_bbox,task):
    tf.reset_default_graph()

    # params
    learning_rate = 0.01
    X = tf.placeholder(tf.float32, shape=(None, 64, 64, 1), name="images")

    if task == 'classify':
        Y = tf.placeholder(tf.float32, shape=(None, 2, 10), name="labels")
        logits = net(X, is_training=True,task='classify')
        prediction = tf.argmax(logits, 2)
        loss_function = tf.nn.softmax_cross_entropy_with_logits(logits=logits, labels=Y)
        loss = tf.reduce_mean(loss_function)
        # calculate accuracy
        accuracy = 100.0 * tf.reduce_mean(tf.cast(tf.equal(prediction, tf.argmax(Y, 2)), dtype=tf.float32))


    elif task == 'detection':
        Y = tf.placeholder(tf.float32, shape=(None, 2, 4), name="labels")
        prediction = net(X, is_training=True, task='detection')

        loss_l2 = tf.reduce_mean(tf.sqrt(tf.reduce_sum(tf.square(tf.subtract(Y, prediction)), axis=2)))
        loss_size1 = tf.reduce_mean(tf.reduce_sum(tf.subtract(prediction[:, :, 2], prediction[:, :, 0]), axis=1)) - 56
        loss_size2 = tf.reduce_mean(tf.reduce_sum(tf.subtract(prediction[:, :, 3], prediction[:, :, 1]), axis=1)) - 56
        loss = loss_l2 + loss_size1 + loss_size2
        # calculate accuracy
        accuracy = 100.0 * tf.reduce_mean(tf.cast(tf.equal(prediction, Y), dtype=tf.float32))


    optimizer = tf.train.AdamOptimizer(learning_rate=learning_rate)
    grads_and_vars = optimizer.compute_gradients(loss, tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES))
    training_operation = optimizer.apply_gradients(grads_and_vars)

    for var in tf.trainable_variables():
        tf.summary.histogram(var.op.name + "/histogram", var)

    add_gradient_summaries(grads_and_vars)
    tf.summary.scalar("loss_operation", loss)
    merged_summary_op = tf.summary.merge_all()

    saver = tf.train.Saver()

    with tf.Session() as sess:
        sess.run(tf.global_variables_initializer())

        batch_size = 100
        n_epochs = 1
        n_batches = 1

        if task == 'classify':
            dataset = data_loader.dataIterator(x_train, y_train, batch_size)
        elif task == 'detection':
            dataset = data_loader.dataIterator(x_train,train_bbox, batch_size)


        for epoch in range(n_epochs):
            for iter in range(n_batches):
                batch_x, batch_y = dataset.next_batch()
                sess.run([training_operation, merged_summary_op], feed_dict={X: batch_x, Y: batch_y})
            valid_acc = 0

            #validation
            for i in range(5):
                if task == 'classify':
                    valid_acc += accuracy.eval(
                    feed_dict={X: x_valid[i * 1000:i * 1000 + 1000], Y: y_valid[i * 1000:i * 1000 + 1000]})
                elif task == 'detection':
                    valid_acc += accuracy.eval(
                        feed_dict={X: x_valid[i * 1000:i * 1000 + 1000], Y: valid_bbox[i * 1000:i * 1000 + 1000]})
            valid_acc /= 5

            acc = accuracy.eval(feed_dict={X: batch_x, Y: batch_y})
            losses = loss.eval(feed_dict={X: batch_x, Y: batch_y})
            print(task +": ",epoch, "Training batch accuracy:", acc, "loss is: ", losses, "valid accuracy is: ", valid_acc)

        saver.save(sess, 'ckpt/', global_step=n_epochs)
