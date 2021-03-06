from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import numpy as np
from collections import deque, OrderedDict

def unflatten(vector, shapes):
  i = 0
  arrays = []
  for shape in shapes:
    size = np.prod(shape)
    array = vector[i:(i + size)].reshape(shape)
    arrays.append(array)
    i += size
  assert len(vector) == i, "Passed weight does not have the correct shape."
  return arrays

class TensorFlowVariables(object):
  """An object used to extract variables from a loss function.

  This object also provides methods for getting and setting the weights of the
  relevant variables.

  Attributes:
    sess (tf.Session): The tensorflow session used to run assignment.
    loss: The loss function passed in by the user.
    variables (List[tf.Variable]): Extracted variables from the loss.
    assignment_placeholders (List[tf.placeholders]): The nodes that weights get
      passed to.
    assignment_nodes (List[tf.Tensor]): The nodes that assign the weights.
    prefix (Bool): Boolean for if there is a prefix on the variable names.
  """
  def __init__(self, loss, sess=None, prefix=False):
    """Creates a TensorFlowVariables instance."""
    import tensorflow as tf
    self.sess = sess
    self.loss = loss
    self.prefix = prefix
    queue = deque([loss])
    variable_names = []

    # We do a BFS on the dependency graph of the input function to find 
    # the variables.
    while len(queue) != 0:
      op = queue.popleft().op
      queue.extend(op.inputs)
      if op.node_def.op == "Variable":
        variable_names.append(op.node_def.name)
    self.variables = OrderedDict()
    for v in [v for v in tf.global_variables() if v.op.node_def.name in variable_names]:
      name = v.op.node_def.name.split("/", 1 if prefix else 0)[-1]
      self.variables[name] = v
    self.assignment_placeholders = dict()
    self.assignment_nodes = []

    # Create new placeholders to put in custom weights.
    for k, var in self.variables.items():
      self.assignment_placeholders[k] = tf.placeholder(var.value().dtype, var.get_shape().as_list())
      self.assignment_nodes.append(var.assign(self.assignment_placeholders[k]))

  def set_session(self, sess):
    """Modifies the current session used by the class."""
    self.sess = sess

  def get_flat_size(self):
    return sum([np.prod(v.get_shape().as_list()) for v in self.variables.values()])

  def _check_sess(self):
    """Checks if the session is set, and if not throw an error message."""
    assert self.sess is not None, "The session is not set. Set the session either by passing it into the TensorFlowVariables constructor or by calling set_session(sess)."
  
  def get_flat(self):
    """Gets the weights and returns them as a flat array."""
    self._check_sess()
    return np.concatenate([v.eval(session=self.sess).flatten() for v in self.variables.values()])
  
  def set_flat(self, new_weights):
    """Sets the weights to new_weights, converting from a flat array."""
    self._check_sess()
    shapes = [v.get_shape().as_list() for v in self.variables.values()]
    arrays = unflatten(new_weights, shapes)
    placeholders = [self.assignment_placeholders[k] for k, v in self.variables.items()]
    self.sess.run(self.assignment_nodes, feed_dict=dict(zip(placeholders,arrays)))

  def get_weights(self):
    """Returns the weights of the variables of the loss function in a list."""
    self._check_sess()
    return {k: v.eval(session=self.sess) for k, v in self.variables.items()}

  def set_weights(self, new_weights):
    """Sets the weights to new_weights."""
    self._check_sess()
    self.sess.run(self.assignment_nodes, feed_dict={self.assignment_placeholders[name]: value for (name, value) in new_weights.items()})
