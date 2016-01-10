import collections
import six
import threading


def merge(destination, source):
    """
    Recursively merges one dict into another.

    If conflicting entries are detected, the values from the `source` dict
    will override those in the `destination`.  If a value is not set in the
    `source` dict, then it will remain unchanged in the `destination`.

    To remove entries with this method, set a value explicitly to `None`.

    :param destination: the dictionary into which values will be inserted
    :type  destination: dict
    :param source: the dictionary from which value will be taken
    :type  source: dict
    :return: the destination dict after the merge
    :rtype:  dict
    """
    for key, value in source.items():
        if value is None:
            del destination[key]
        elif key not in destination:
            destination[key] = value
        else:
            if isinstance(value, dict):
                merge(destination[key], value)
            else:
                destination[key] = value

    return destination


class ObservableDict(dict):
    """
    Creates a tree of dict-likes that support merge and observe operations.

    An ObservableDict is a tree data structure that operated similarly to a
    python dict with the addition of two features:
    1) Callbacks can 'observe' changes using observe() and unobserve()
    2) A merge() function allows modification of a sparse set of keys.

    If a dict or tree of dicts is added as the value of a key, they will be
    converted to a corresponding tree of ObservableDicts which have the above
    functionality.
    """
    def __init__(self, parent=None, key=None, entries=None):
        dict.__init__(self)

        if parent is None and key is not None:
            raise ValueError("Cannot specify a key without a parent dict.")
        self._parent = parent
        self._key = key

        self._dirty = set()
        self._observer_lock = threading.Lock()
        self._observers = collections.defaultdict(lambda: set())

        # The builtin dict.__init__ method does not call dict.update, which
        # would bypass the dict type-conversion and notification systems.
        # So we override this behavior with the following manual update.
        self.update(entries)

    def __setitem__(self, key, value):
        if isinstance(value, dict):
            value = ObservableDict(parent=self, key=key, entries=value.items())
        dict.__setitem__(self, key, value)
        self.dirty(key)

    def update(self, *args, **kwargs):
        # The builtin dict.update method does not call dict.__setitem__, which
        # would bypass the dict type-conversion needed there.  So we override
        # this behavior with the following manual iteration of entries.
        for k, v in six.viewitems(dict(*args, **kwargs)):
            self[k] = v

    def cleanup(self):
        """
        Removes unused key references from this dictionary.

        Entries are generated and stored on-the-fly to improve performance
        on queries even for nonexistent data.  This method removes entries
        that contain no data or observation listeners.

        Note: This process will orphan references to subtrees of this
        dictionary that no longer contain data.  Do not call this method
        unless you are sure no references to intermediate subtrees are 
        still being used.

        :return: True if this key no longer contains any data
        :rtype:  bool
        """
        # Cleanup all of the child dictionaries.
        for key, value in self.items():
            if isinstance(value, ObservableDict):
                if value.cleanup():
                    value._parent = None
                    del self[key]

        # If there are no remaining references, flag this object as empty.
        return not self.keys() and not len(self._observers)

    def dirty(self, key):
        """
        Indicate that this key in the observer dict has been dirtied.

        This will trigger notifications on any observers of this subtree on
        the next notify() call.

        :param key: the key that has been modified
        :type  key: any
        """
        with self._observer_lock:
            self._dirty.add(key)
            if self._parent:
                self._parent.dirty(self._key)
            print(('dirty: ', self.path, '>', key))

    def notify(self):
        """
        Notify callbacks on all dirtied subtrees of this branch.

        This calls registered observer functions on any subtree that has been
        modified since the last notify call.
        """
        with self._observer_lock:
            for key in self._dirty:
                value = self[key]

                # Allow child subtrees to perform notification.
                if isinstance(value, ObservableDict):
                    value.notify()

                # Perform notification for observers of this entry.
                path = self.path + (key,)
                for observer in self._observers[key]:
                    observer(path, value)

    def observe(self, key, callback):
        """
        Adds an observer of changes to the given path in the dict.
        :param key: the key in this dict to observe
        :type  key: any
        :param callback: a function that will be called if the key changes
        :type  callback: (key, value) -> None
        """
        with self._observer_lock:
            self._observers[key].add(callback)

    def unobserve(self, key, callback):
        """
        Removes an observer of changes from the given path in the dict.
        :param key: the key in this dict to stop observing
        :type  key: any
        :param callback: a function that will not be called if the key changes
        :type  callback: (key, value) -> None
        """
        with self._observer_lock:
            try:
                self._observers[key].remove(callback)
                if not len(self._observers[key]):
                    del self._observers[key]
            except KeyError:
                raise ValueError('Attempted to remove unregistered callback.')

    def merge(self, d):
        """
        Recursively merges a dict into this object.

        If conflicting entries are detected, the values from the provided dict
        will override the ones in this object.  If a value is not set in the
        provided dict, then it will remain unchanged in this object.

        To remove entries with this method, set a value explicitly to `None`.

        :param d: the dictionary from which value will be taken
        :type  d: dict
        """
        merge(self, d)

    @property
    def path(self):
        """
        :return: a tuple of keys representing the path to this entry
        :rtype:  (str)
        """
        if self._parent is not None:
            return self._parent.path + (self._key,)
        else:
            return ()