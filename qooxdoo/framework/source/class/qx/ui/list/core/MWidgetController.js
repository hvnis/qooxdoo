/* ************************************************************************

   qooxdoo - the new era of web development

   http://qooxdoo.org

   Copyright:
     2004-2010 1&1 Internet AG, Germany, http://www.1und1.de

   License:
     LGPL: http://www.gnu.org/licenses/lgpl.html
     EPL: http://www.eclipse.org/org/documents/epl-v10.php
     See the LICENSE file in the project's top-level directory for details.

   Authors:
     * Christian Hagendorn (chris_schmidt)
     * Martin Wittemann (martinwittemann)

************************************************************************ */

/**
 * The mixin controls the binding between model and item.
 *
 * @internal
 */
qx.Mixin.define("qx.ui.list.core.MWidgetController",
{
  construct : function() {
    this.__boundItems = [];
  },


  properties :
  {
    /**
     * The path to the property which holds the information that should be
     * shown as a label. This is only needed if objects are stored in the model.
     */
    labelPath :
    {
      check: "String",
      nullable: true
    },


    /**
     * The path to the property which holds the information that should be
     * shown as a icon. This is only needed if objects are stored in the model
     * and if the icon should be shown.
     */
    iconPath :
    {
      check: "String",
      nullable: true
    },


    /**
     * A map containing the options for the label binding. The possible keys
     * can be found in the {@link qx.data.SingleValueBinding} documentation.
     */
    labelOptions :
    {
      nullable: true
    },


    /**
     * A map containing the options for the icon binding. The possible keys
     * can be found in the {@link qx.data.SingleValueBinding} documentation.
     */
    iconOptions :
    {
      nullable: true
    },


    /**
     * Delegation object, which can have one or more functions defined by the
     * {@link qx.ui.list.core.IControllerDelegate} interface.
     */
    delegate :
    {
      event: "changeDelegate",
      init: null,
      nullable: true
    }
  },


  members :
  {
    /** {Array} which contains the bounded items */
    __boundItems : null,


    /**
     * Helper-Method for binding the default properties (label and icon) from
     * the model to the target widget.
     *
     * This method should only be called in the
     * {@link IControllerDelegate#bindItem} function
     * implemented by the {@link #delegate} property.
     *
     * @param item {qx.ui.form.ListItem} The internally created and used
     *   ListItem.
     * @param index {Integer} The index of the ListItem.
     */
    bindDefaultProperties : function(item, index)
    {
      // bind model first
      this.bindProperty(
        "", "model", null, item, index
      );

      this.bindProperty(
        this.getLabelPath(), "label", this.getLabelOptions(), item, index
      );

      if (this.getIconPath() != null) {
        this.bindProperty(
          this.getIconPath(), "icon", this.getIconOptions(), item, index
        );
      }
    },


    /**
     * Helper-Method for binding a given property from the model to the target
     * widget.
     * This method should only be called in the
     * {@link IControllerDelegate#bindItem} function implemented by the
     * {@link #delegate} property.
     *
     * @param sourcePath {String | null} The path to the property in the model.
     * @param targetProperty {String} The name of the property in the target widget.
     * @param options {Map | null} The options to use for the binding.
     * @param targetWidget {qx.ui.core.Widget} The target widget.
     * @param index {Integer} The index of the current binding.
     */
    bindProperty : function(sourcePath, targetProperty, options, targetWidget, index)
    {
      var type = targetWidget.getUserData("cell.type")
      var bindPath = this.__getBindPath(index, sourcePath, type);

      var bindTarget = this._list;
      if (type == "group") {
        bindTarget = this._list._groups;
      }

      var id = bindTarget.bind(bindPath, targetWidget, targetProperty, options);
      this.__addBinding(targetWidget, id);
    },


    /**
     * Helper-Method for binding a given property from the target widget to
     * the model.
     * This method should only be called in the
     * {@link IControllerDelegate#bindItem} function implemented by the
     * {@link #delegate} property.
     *
     * @param targetPath {String | null} The name of the property in the target.
     * @param sourcePath {String} The path to the property in the model.
     * @param options {Map | null} The options to use for the binding.
     * @param sourceWidget {qx.ui.core.Widget} The source widget.
     * @param index {Integer} The index of the current binding.
     */
    bindPropertyReverse: function(targetPath, sourcePath, options, sourceWidget, index)
    {
      var type = sourceWidget.getUserData("cell.type")
      var bindPath = this.__getBindPath(index, targetPath, type);

      var id = sourceWidget.bind(sourcePath, this, bindPath, options);
      this.__addBinding(sourceWidget, id);
    },


    /**
     * Remove all bindings from all bounded items.
     */
    removeBindings : function()
    {
      while(this.__boundItems.length > 0) {
        var item = this.__boundItems.pop();
        this._removeBindingsFrom(item);
      }
    },


    /**
     * Configure the passed item if a delegate is set and the needed
     * function {@link IControllerDelegate#configureItem} is available.
     *
     * @param item {qx.ui.core.Widget} item to configer.
     */
    _configureItem : function(item)
    {
      var delegate = this.getDelegate();

      if (delegate != null && delegate.configureItem != null) {
        delegate.configureItem(item);
      }
    },


    /**
     * Sets up the binding for the given item and index.
     *
     * @param item {qx.ui.core.Widget} The internally created and used item.
     * @param index {Integer} The index of the item.
     */
    _bindItem : function(item, index) {
      var delegate = this.getDelegate();

      if (delegate != null && delegate.bindItem != null) {
        delegate.bindItem(this, item, index);
      } else {
        this.bindDefaultProperties(item, index);
      }
    },


    /**
     * Sets up the binding for the given group item and index.
     *
     * @param item {qx.ui.core.Widget} The internally created and used item.
     * @param index {Integer} The index of the item.
     */
    _bindGroupItem : function(item, index) {
      var delegate = this.getDelegate();

      if (delegate != null && delegate.bindGroupItem != null) {
        delegate.bindGroupItem(this, item, index);
      } else {
        this.bindProperty(null, "value", null, item, index);
      }
    },


    /**
     * Removes the binding of the given item.
     *
     * @param item {qx.ui.core.Widget} The item which the binding should
     *   be removed.
     */
    _removeBindingsFrom : function(item) {
      var bindings = this.__getBindings(item);

      while (bindings.length > 0) {
        var id = bindings.pop();

        try {
          this._list.removeBinding(id);
        } catch(e) {
          try {
            this._list._groups.removeBinding(id);
          } catch(e) {
            item.removeBinding(id);
          }
        }
      }

      if (qx.lang.Array.contains(this.__boundItems, item)) {
        qx.lang.Array.remove(this.__boundItems, item);
      }
    },


    /**
     * Helper method to create the path for binding.
     *
     * @param index {Integer} The index of the item.
     * @param path {String|null} The path to the property.
     * @param path {String} The type <code>["item", "group"]</code>.
     */
    __getBindPath : function(index, path, type)
    {
      var bindPath = "model[" + index + "]";
      if (type == "group") {
        bindPath = "[" + index + "]";
      }

      if (path != null && path != "") {
        bindPath += "." + path;
      }

      return bindPath;
    },


    /**
     * Helper method to save the binding for the widget.
     *
     * @param widget {qx.ui.core.Widget} widget to save binding.
     * @param id {var} the id from the binding.
     */
    __addBinding : function(widget, id)
    {
      var bindings = this.__getBindings(widget);

      if (!qx.lang.Array.contains(bindings, id)) {
        bindings.push(id);
      }

      if (!qx.lang.Array.contains(this.__boundItems, widget)) {
        this.__boundItems.push(widget);
      }
    },


    /**
     * Helper method which returns all bound id from the widget.
     *
     * @param widget {qx.ui.core.Widget} widget to get all binding.
     * @return {Array} all bound id's.
     */
    __getBindings : function(widget)
    {
      var bindings = widget.getUserData("BindingIds");

      if (bindings == null) {
        bindings = [];
        widget.setUserData("BindingIds", bindings);
      }

      return bindings;
    }
  },


  destruct : function() {
    this.__boundItems = null;
  }
});
