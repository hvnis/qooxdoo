#!/usr/bin/env python
# -*- coding: utf-8 -*-
################################################################################
#
#  qooxdoo - the new era of web development
#
#  http://qooxdoo.org
#
#  Copyright:
#    2006-2012 1&1 Internet AG, Germany, http://www.1und1.de
#
#  License:
#    LGPL: http://www.gnu.org/licenses/lgpl.html
#    EPL: http://www.eclipse.org/org/documents/epl-v10.php
#    See the LICENSE file in the project's top-level directory for details.
#
#  Authors:
#    * Thomas Herchenroeder (thron7)
#
################################################################################

##
# AST checking, for unknown globals etc.
##

import os, sys, re, types, itertools
from collections import defaultdict
from ecmascript.frontend import treeutil, lang, Comment
from ecmascript.frontend import tree, treegenerator
from ecmascript.transform.optimizer import variantoptimizer
from ecmascript.transform.check  import scopes
from ecmascript.transform.check  import jshints
from ecmascript.transform.check  import global_symbols as gs
from generator.runtime.CodeIssue import CodeIssue

class LintChecker(treeutil.NodeVisitor):

    def __init__(self, root_node, file_name_, opts):
        super(LintChecker, self).__init__()
        self.root_node = root_node
        self.file_name = file_name_  # it's a warning module, so i need a proper file name
        self.opts = opts
        self.issues = []
        self.known_globals_bases = (
            self.opts.library_classes + self.opts.allowed_globals + lang.QXGLOBALS )
        global file_name
        file_name = file_name_

    def visit_file(self, node):
        # we can run the basic scope checks as with function nodes
        if not self.opts.ignore_undefined_globals:
            self.unknown_globals(node.scope)
        if not self.opts.ignore_shadowing_locals:
            self.locals_shadowing_globals(node.scope)
        self.function_unused_vars(node)
        if not self.opts.ignore_deprecated_symbols:
            self.function_used_deprecated(node)
        if not self.opts.ignore_multiple_vardecls:
            self.function_multiple_var_decls(node)
        # this is also good to check class map integrity
        for class_defn in treeutil.findQxDefineR(node):
            if not self.opts.ignore_undeclared_privates:
                self.class_declared_privates(class_defn)
            if not self.opts.ignore_reference_fields:
                self.class_reference_fields(class_defn)
        # check all qx.core.Environment calls
        self.environment_check_calls(node)
        # recurse
        for cld in node.children:
            self.visit(cld)

    def visit_map(self, node):
        #print "visiting", node.type
        if not self.opts.ignore_multiple_mapkeys:
            self.map_unique_keys(node)
        # recurse
        for cld in node.children:
            self.visit(cld)

    def visit_loop(self, node):
        #print "visiting", node.type
        if not self.opts.ignore_no_loop_block:
            self.loop_body_block(node.getChild("body")) # all "loops" have at least one body
            if node.get("loopType")=="IF" and len(node.children)>2:  # there is an "else"
                self.loop_body_block(node.children[2])
        # recurse
        for cld in node.children:
            self.visit(cld)

    def visit_function(self, node):
        #print "visiting", node.type
        if not self.opts.ignore_undefined_globals:
            self.unknown_globals(node.scope)
        if not self.opts.ignore_shadowing_locals:
            self.locals_shadowing_globals(node.scope)
        self.function_unused_vars(node)  # self.opts are applied in the function
        if not self.opts.ignore_deprecated_symbols:
            self.function_used_deprecated(node)
        if not self.opts.ignore_multiple_vardecls:
            self.function_multiple_var_decls(node)
        # recurse
        for cld in node.children:
            self.visit(cld)

    def visit_catch(self, node):
        if not self.opts.ignore_catch_param:
            self.catch_param_shadowing(node)
        # recurse
        for cld in node.children:
            self.visit(cld)

    def visit_finally(self, node):
        if not self.opts.ignore_finally_without_catch:
            self.finally_without_catch(node)
        # recurse
        for cld in node.children:
            self.visit(cld)

    # - ---------------------------------------------------------------------------

    def function_used_deprecated(self, funcnode):
        # take advantage of Scope() objects
        scope = funcnode.scope
        for id_, scopeVar in scope.globals().items():
            # id_ might be an incomplete class id, like "qx"
            # let's look at the var uses
            for var_node in scopeVar.uses:
                full_name = (treeutil.assembleVariable(var_node))[0]
                ok = True
                if (full_name in lang.GLOBALS # JS built-ins ('alert' etc.)
                        and full_name in lang.DEPRECATED):
                    ok = False
                    at_hints = get_at_hints(var_node) # check full_name against @ignore hints
                    if at_hints:
                        ok = self.is_name_lint_filtered(full_name, at_hints, "ignoreDeprecated")
                if not ok:
                    issue = warn("Deprecated global symbol used: '%s'" % full_name, self.file_name, var_node)
                    issue.name = full_name  # @deprecated {3.0} to filter against #ignore later
                    self.issues.append(issue)

    def unknown_globals(self, scope):
        # collect scope's global use locations
        global_nodes = defaultdict(list)  # {assembled: [node]}
        for id_, scopeVar in scope.globals().items():
            for head_node in scopeVar.uses:
                var_top = treeutil.findVarRoot(head_node)
                full_name = (treeutil.assembleVariable(var_top))[0]
                global_nodes[full_name].append(head_node)
        # filter allowed globals
        # - from config
        global_nodes = dict([(key,nodes) for (key,nodes) in global_nodes.items()
            if key not in self.opts.allowed_globals])
        # - from known classes and namespaces
        global_nodes = dict([(key,nodes) for (key,nodes) in global_nodes.items()
            if not extension_match_in(key, self.known_globals_bases, self.opts.class_namespaces)]) # known classes (classList + their namespaces)
        # - from built-ins
        new_keys = gs.globals_filter_by_builtins(global_nodes.keys())
        global_nodes = dict([(key,nodes) for (key,nodes) in global_nodes.items()
            if key in new_keys])
        # - with jshints
        for key, nodes in global_nodes.items():
            global_nodes[key] = [node for node in nodes 
                if not gs.ident_is_ignored(key, node)]
        # warn remaining
        for key, nodes in global_nodes.items():
            for node in nodes:
                issue = warn("Unknown global symbol used: '%s'" % key, self.file_name, node)
                issue.name = key # @deprecated {3.0} to filter against #ignore later
                self.issues.append(issue)


    def locals_shadowing_globals(self, scope):
        result = []
        # collect scope's locals
        local_nodes = dict(scope.locals().items())
        # - match known top-level library symbols
        known_qx_names = set([x.split('.')[0] for x in self.opts.library_classes]) # includes q, qxWeb
        r = [key for key in local_nodes.keys() if key in known_qx_names]
        result.extend(r)

        # - match built-ins -- currently disabled
        #free_names = gs.globals_filter_by_builtins(local_nodes.keys())
        #r = [key for key in local_nodes.keys() if key not in free_names]
        #result.extend(r)

        # warn what we have
        for key, scopeVar in local_nodes.items():
            if key in result:
                for node in scopeVar.occurrences():
                    issue = warn("Local var shadowing a library symbol: '%s'" % key, self.file_name, node)
                    self.issues.append(issue)


    def function_unused_vars(self, funcnode):
        scope = funcnode.scope
        unused_vars = dict([(id_, scopeVar) for id_, scopeVar in scope.vars.items()
                                if self.var_unused(scopeVar)])

        for var_name,scopeVar in unused_vars.items():
            ok = False
            if scopeVar.is_param and self.opts.ignore_unused_parameter:
                ok = True
            elif not scopeVar.is_param and self.opts.ignore_unused_variables:
                ok = True
            else:
                at_hints = get_at_hints(funcnode) # check @ignore hints
                if at_hints:
                    ok = self.is_name_lint_filtered(var_name, at_hints, "ignoreUnused")
            if not ok:
                issue = warn("Declared but unused variable or parameter: '%s'" % var_name, self.file_name, scopeVar.decl[0])
                self.issues.append(issue)

    ##
    # <name> is an extension match of <prefix> .iff. <prefix> is a prefix of <name>
    #
    # taking object boundaries (".") into account, i.e.
    # "a" is a prefix match of "a" and "a.b", but not of "ab"
    #
    @staticmethod
    def extension_match(name, prefix):
        return re.match(r"%s(?:\.|$)" % re.escape(prefix), name)

    ##
    # Checks the @lint hints in <at_hints> if the given <var_name> is filtered
    # under the <filter_key> (e.g. "ignoreUndefined" in *@lint ignoreUndefined(<var_name>))
    #
    def is_name_lint_filtered(self, var_name, at_hints, filter_key):
        filtered = False
        if at_hints:
            if ( 'lint' in at_hints and
                filter_key in at_hints['lint']):
                if any([self.extension_match(var_name, x) for x in at_hints['lint'][filter_key]]):
                    filtered = True
        return filtered


    ##
    # Check if a map only has unique keys.
    #
    def map_unique_keys(self, node):
        # all children are .type "keyvalue", with .get(key) = <identifier>
        entries = [(keyval.get("key"), keyval) for keyval in node.children]
        seen = set()
        for key,keyval in entries:
            if key in seen:
                issue = warn("Duplicate use of map key", self.file_name, keyval)
                self.issues.append(issue)
            seen.add(key)

    def function_multiple_var_decls(self, node):
        scope_node = node.scope
        for id_, var_node in scope_node.vars.items():
            if self.multiple_var_decls(var_node):
                issue = warn("Multiple declarations of variable: '%s' (%r)" % (
                    id_, [n.get("line",-1) for n in var_node.decl]), self.file_name, None)
                self.issues.append(issue)

    def multiple_var_decls(self, scopeVar):
        return len(scopeVar.decl) > 1

    def var_unused(self, scopeVar):
        return len(scopeVar.decl) > 0 and len(scopeVar.uses) == 0

    def loop_body_block(self, body_node):
        def is_else_body(body_node):
            return  (len(body_node.parent.children)==3  # parent loop has an 'else' part
                and body_node == body_node.parent.children[2] # the current node is the 'else' part
            )
        def child_is_if(body_node):
            return (body_node.children[0].type == "loop"
                and body_node.children[0].get("loopType") == "IF"
            )

        if not body_node.getChild("block",0):
            ok = False
            # allow "else if"
            if is_else_body(body_node) and child_is_if(body_node):
                ok = True
            else:
                # check @hints
                scope_node = scopes.find_enclosing(body_node)
                if scope_node:
                    at_hints = get_at_hints(scope_node.node)
                    if at_hints and 'lint' in at_hints and 'ignoreNoLoopBlock' in at_hints['lint']:
                        ok = True
            if not ok:
                issue = warn("Loop or condition statement without a block as body", self.file_name, body_node)
                self.issues.append(issue)

    ##
    # Check that no privates are used in code that are not declared as a class member
    #
    this_aliases = ('this', 'that')
    reg_privs = re.compile(r'\b__')

    def class_declared_privates(self, class_def_node):
        try:
            class_map = treeutil.getClassMap(class_def_node)
        except tree.NodeAccessException:
            return

        for category in ('statics', 'members'):
            # collect all privates
            if category in class_map:
                private_keys = set()
                for key in class_map[category]:
                    if self.reg_privs.match(key):
                        private_keys.add(key)
                # go through uses of 'this' and 'that' that reference a private
                items = class_map[category].items()
                if category == "members" and 'construct' in class_map: # add checking constructor
                    items.insert(0, ('construct', class_map['construct'].parent  # to recover (value ...)
                        ))
                for key,val in items:
                    if val.children[0].type == 'function':
                        function_privs = self.function_uses_local_privs(val.children[0])
                        for priv, node in function_privs:
                            if priv not in private_keys:
                                issue = warn("Using an undeclared private class feature: '%s'" % priv, self.file_name, node)
                                self.issues.append(issue)


    ##
    # Warn about reference types in map values, as they are shared across instances.
    #
    def class_reference_fields(self, class_def_node):
        try:
            class_map = treeutil.getClassMap(class_def_node)
        except tree.NodeAccessException:
            return
        # only check members
        members_map = class_map['members'] if 'members' in class_map else {}

        for key, val in members_map.items():
            value_node = val.children[0]
            if (value_node.type in ("map", "array") or
                (value_node.type == "operation" and value_node.get("operator")=="NEW")):
                ok = False
                at_hints = get_at_hints(value_node)
                if at_hints:
                    ok = self.is_name_lint_filtered(key, at_hints, "ignoreReferenceField")
                if not ok:
                    issue = warn("Reference values are shared across all instances: '%s'" % key, self.file_name, value_node)
                    self.issues.append(issue)


    def function_uses_local_privs(self, func_node):
        function_privs = set()
        reg_this_aliases = re.compile(r'\b%s' % "|".join(self.this_aliases))
        scope = func_node.scope
        for id_,scopeVar in scope.vars.items():
            if reg_this_aliases.match(id_):
                for var_use in scopeVar.uses:
                    full_name = treeutil.assembleVariable(var_use)[0]
                    name_parts = full_name.split(".")
                    if len(name_parts) > 1 and self.reg_privs.match(name_parts[1]):
                        function_privs.add((name_parts[1],var_use))
        return function_privs

    def environment_check_calls(self, node):
        for env_call in variantoptimizer.findVariantNodes(node):
            variantMethod = env_call.toJS(treegenerator.PackerFlags).rsplit('.',1)[1]
            callNode = treeutil.selectNode(env_call, "../..")
            if variantMethod in ["select"]:
                self.environment_check_select(callNode)
            elif variantMethod in ["get"]:
                self.environment_check_get(callNode)
            elif variantMethod in ["filter"]:
                self.environment_check_filter(callNode)

    def environment_check_select(self, select_call):
        if select_call.type != "call":
            return False

        params = select_call.getChild("arguments")
        if len(params.children) != 2:
            issue = warn("qx.core.Environment.select: takes exactly two arguments.", self.file_name, select_call)
            self.issues.append(issue)
            return False

        # Get the variant key from the select() call
        firstParam = params.getChildByPosition(0)
        #evaluate.evaluate(firstParam)
        #firstValue = firstParam.evaluated
        #if firstValue == () or not isinstance(firstValue, types.StringTypes):
        if not treeutil.isStringLiteral(firstParam):
            ok = False
            if self.opts.ignore_environment_nonlit_key:
                ok = True
            else:
                lint_key = "environmentNonLiteralKey"
                at_hints = get_at_hints(select_call)
                if at_hints:
                    if ((lint_key in at_hints['lint'] and not len(at_hints['lint'][lint_key]))     # environmentNonLiteralKey()
                        or self.is_name_lint_filtered(firstParam.toJS(None), at_hints, lint_key)): # environmentNonLiteralKey(foo)
                        ok = True
            if not ok:
                issue = warn("qx.core.Environment.select: first argument is not a string literal.", self.file_name, select_call)
                self.issues.append(issue)
            return False

        # Get the resolution map, keyed by possible variant key values (or value expressions)
        secondParam = params.getChildByPosition(1)
        default = None
        found = False
        if secondParam.type == "map":
            # we could try to check a relevant key from a variantsMap against the possibilities in the code
            # like in variantoptimzier - deferred
            pass
        else:
            issue = warn("qx.core.Environment.select: second parameter is not a map.", self.file_name, select_call)
            self.issues.append(issue)


    def environment_check_get(self, get_call):

        # Simple sanity checks
        params = get_call.getChild("arguments")
        if len(params.children) != 1:
            issue = warn("qx.core.Environment.get: takes exactly one argument.", self.file_name, get_call)
            self.issues.append(issue)
            return False

        firstParam = params.getChildByPosition(0)
        if not treeutil.isStringLiteral(firstParam):
            ok = False
            if self.opts.ignore_environment_nonlit_key:
                ok = True
            else:
                lint_key = "environmentNonLiteralKey"
                at_hints = get_at_hints(get_call)
                if at_hints:
                    if ((lint_key in at_hints['lint'] and not len(at_hints['lint'][lint_key]))     # environmentNonLiteralKey()
                        or self.is_name_lint_filtered(firstParam.toJS(None), at_hints, lint_key)): # environmentNonLiteralKey(foo)
                        ok = True
            if not ok:
                issue = warn("qx.core.Environment.get: first argument is not a string literal.", self.file_name, get_call)
                self.issues.append(issue)
            return False

        # we could try to verify the key, like in variantoptimizer


    def environment_check_filter(self, filter_call):

        def isExcluded(mapkey, variantMap):
            return mapkey in variantMap and bool(variantMap[mapkey]) == False

        complete = False
        if filter_call.type != "call":
            return complete

        params = filter_call.getChild("arguments")
        if len(params.children) != 1:
            issue = warn("qx.core.Environment.filter: takes exactly one argument.", self.file_name, filter_call)
            self.issues.append(issue)
            return complete

        # Get the map from the filter call
        firstParam = params.getChildByPosition(0)
        if not firstParam.type == "map":
            issue = warn("qx.core.Environment.filter: first argument is not a map.", self.file_name, filter_call)
            self.issues.append(issue)
            return complete

        # we could now try to verify the keys in the map - deferred
        return True

    ##
    # Check if catch param ("e") shadows another variable in the current
    # scope (bug#1207, with IE)
    def catch_param_shadowing(self, catch_node):
        catch_param = catch_node.getChild("params")
        if catch_param.children and catch_param.children[0].type == 'identifier':
            catch_param = catch_param.children[0]
        else:
            catch_param = None  # this would be against spec
        if catch_param:
            higher_scope = catch_param.scope.parent.lookup(catch_param.get("value")) # want to look at scopes *above* the catch scope
            if higher_scope: # "e" has been registered with a higher scope, either as decl'ed or global
                issue = warn("Shadowing scoped var with catch parameter (bug#1207): %s" % 
                    catch_param.get("value"), self.file_name, catch_param)
                self.issues.append(issue)
            
    ##
    # Check for try-finally without 'catch' block (issue in older IE, s. bug#3688)
    #
    def finally_without_catch(self, finally_node):
        try_node = finally_node.parent
        if not try_node.getChild("catch", 0):
            issue = warn("A finally clause without a catch might not be run (bug#3688)",
                self.file_name, finally_node)
            self.issues.append(issue)
            

# - ---------------------------------------------------------------------------

def warn(msg, fname, node):
    issue = CodeIssue()
    issue.msg = msg
    if node:
        issue.line, issue.column = node.get("line"), node.get("column")
    return issue

##
# Get the JSDoc comments in a nested dict structure
def get_at_hints(node, at_hints=None):
    if at_hints is None:
        at_hints = defaultdict(dict)
    commentsArray = Comment.parseNode(node, process_txt=False)  # searches comment "around" this node
    for commentAttributes in commentsArray:
        for entry in commentAttributes:
             # {'arguments': ['a', 'b'],
             #  'category': u'lint',
             #  'functor': u'ignoreReferenceField',
             #  'text': u'<p>ignoreReferenceField(a,b)</p>'
             # }
            cat = entry['category']
            if cat=='lint':
                functor = entry['functor']
                if functor not in at_hints[cat]:
                    at_hints[cat][functor] = set()
                at_hints[cat][functor].update(entry['arguments']) 
            elif cat=="ignore":
                if cat not in at_hints:
                    at_hints[cat] = set()
                at_hints[cat].update(entry['arguments'])
    # include @hints of parent scopes
    scope = scopes.find_enclosing(node)
    if scope:
        at_hints = get_at_hints(scope.node, at_hints)
    return at_hints


def defaultOptions():
    class LintOptions(object): pass
    opts = LintOptions()
    opts.library_classes = [] # with library classes, more exact checks beneath the left-most global are possible
    opts.class_namespaces = [] # TODO: could be computed?!
    opts.allowed_globals = []
    opts.ignore_catch_param = False
    opts.ignore_deprecated_symbols = False
    opts.ignore_environment_nonlit_key = False
    opts.ignore_finally_without_catch = False
    opts.ignore_multiple_mapkeys = False
    opts.ignore_multiple_vardecls= True
    opts.ignore_no_loop_block = False
    opts.ignore_reference_fields = False
    opts.ignore_undeclared_privates = False
    opts.ignore_undefined_globals = False
    opts.ignore_shadowing_locals = False
    opts.ignore_unused_parameter = True
    opts.ignore_unused_variables = False
    opts.warn_unknown_jsdoc_keys = False
    opts.warn_jsdoc_key_syntax   = True

    return opts

##
# A known qx global is either exactly a name space, or a dotted identifier that
# is a dotted extension of a known class.
#
# (This is a copy of MClassDependencies._splitQxClass).
#
def extension_match_in(name, name_list, name_spaces):
    res_name = ''
    res_attribute = ''
    # check for a name space match
    if name in name_spaces:
        res_name = name
    # see if name is a (dot-exact) prefix of any of name_list
    else:
        for class_name in name_list:
            if (name.startswith(class_name) and 
                    re.search(r'^%s\b' % re.escape(class_name), name)): 
                    # re.escape for e.g. the '$' in 'qx.$$'
                    # '\b' so that 'mylib.Foo' doesn't match 'mylib.FooBar'
                if len(class_name) > len(res_name): # take the longest match (?!)
                    res_name = class_name
                    ## compute the 'attribute' suffix
                    #res_attribute = name[ len(class_name) +1:]  # skip class_name + '.'
                    ## see if res_attribute is chained, too
                    #dotidx = res_attribute.find(".")
                    #if dotidx > -1:
                    #    res_attribute = res_attribute[:dotidx]    # only use the first component

    return res_name

# - ---------------------------------------------------------------------------

def lint_check(node, file_name, opts):
    node = scopes.create_scopes(node)  # update scopes
    if not hasattr(node, 'hint'):
        node = jshints.create_hints_tree(node)
    lint = LintChecker(node, file_name, opts)
    lint.visit(node)
    return lint.issues
