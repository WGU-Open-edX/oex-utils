/* eslint-disable prefer-destructuring */
/* eslint-disable no-param-reassign */
/* eslint-disable no-console */
/**
 * Codemod: Replace injectIntl HOC with useIntl hook
 *
 * Handles:
 * - Removes injectIntl and intlShape imports
 * - Removes `intl` from component params, propTypes, defaultProps
 * - Adds useIntl hook in function body if intl is used
 * - Preserves other HOCs like connect()
 */

module.exports = function transformer(fileInfo, { j }) {
  const root = j(fileInfo.source);

  const INTL_SOURCE = '@edx/frontend-platform/i18n';
  const INJECT_INTL = 'injectIntl';
  const INTL_SHAPE = 'intlShape';
  const USE_INTL = 'useIntl';

  let injectIntlImported = false;
  let intlUsed = false;
  let removedIntlParam = false;

  const findIntlWrappedComponent = () => {
    const wrappedComponents = [];

    // Recursive function to find the innermost Identifier in nested HOCs
    function getInnermostComponentName(node) {
      if (j.Identifier.check(node)) {
        return node.name;
      }
      if (j.CallExpression.check(node)) {
        const args = node.arguments;
        if (args.length > 0) {
          return getInnermostComponentName(args[args.length - 1]);
        }
      }
      return null;
    }

    root.find(j.CallExpression, {
      callee: {
        type: 'Identifier',
        name: 'injectIntl',
      },
    }).forEach(path => {
      const wrapped = path.node.arguments[0];
      const componentName = getInnermostComponentName(wrapped);
      if (componentName) {
        wrappedComponents.push(componentName);
      }
    });

    return wrappedComponents;
  };

  console.log('Intl Modernizer starting...');
  // 0. List all components wrapped with injectIntl
  const componentsWithInjectIntl = findIntlWrappedComponent();
  console.log(`Found ${componentsWithInjectIntl.length} component(s) to update: ${componentsWithInjectIntl}`);

  if (componentsWithInjectIntl.length === 0) {
    console.log('No components found!');
    return;
  }

  // 1. Check for usage of `intl`
  console.log('Checking intl usage...');
  root.find(j.Identifier, { name: 'intl' }).forEach((path) => {
    const parent = path.parent.node;
    if (
      !(j.Property.check(parent) && parent.key === path.node)
      && !(j.ObjectPattern.check(path.parentPath.node))
    ) {
      intlUsed = true;
    }
  });

  // 2. Add useIntl import if intl is used
  console.log('Adding useIntl import if needed...');
  if (intlUsed) {
    const existingIntlImport = root.find(j.ImportDeclaration, {
      source: { value: INTL_SOURCE },
    });

    if (existingIntlImport.size() > 0) {
      existingIntlImport.forEach((path) => {
        const alreadyImported = path.node.specifiers.some(
          (s) => s.imported?.name === USE_INTL,
        );
        if (!alreadyImported) {
          path.node.specifiers.push(j.importSpecifier(j.identifier(USE_INTL)));
        }
      });
    } else {
      // No existing import block
      const newImport = j.importDeclaration(
        [j.importSpecifier(j.identifier(USE_INTL))],
        j.literal(INTL_SOURCE),
      );
      root.get().node.program.body.unshift(newImport);
    }
  }

  // 3. Remove injectIntl and intlShape from import { ... } from '@edx/frontend-platform/i18n'
  console.log('Removing unused intl imports...');
  root.find(j.ImportDeclaration, { source: { value: INTL_SOURCE } }).forEach((importPath) => {
    const newSpecifiers = importPath.node.specifiers.filter((specifier) => {
      if (specifier.imported.name === INJECT_INTL) { injectIntlImported = true; }
      return ![INJECT_INTL, INTL_SHAPE].includes(specifier.imported.name);
    });
    if (newSpecifiers.length === 0) {
      j(importPath).remove();
    } else {
      importPath.node.specifiers = newSpecifiers;
    }
  });

  // 4. Remove `intl` from propTypes and defaultProps
  console.log('Removng `intl` from propTypes and defaultProps...');
  root.find(j.AssignmentExpression, {
    left: {
      type: 'MemberExpression',
      object: { name: () => true },
      property: { name: 'propTypes' },
    },
  }).forEach((path) => {
    const props = path.node.right.properties;
    path.node.right.properties = props.filter((prop) => prop.key.name !== 'intl');
  });

  root.find(j.AssignmentExpression, {
    left: {
      type: 'MemberExpression',
      object: { name: () => true },
      property: { name: 'defaultProps' },
    },
  }).forEach((path) => {
    const props = path.node.right.properties;
    path.node.right.properties = props.filter((prop) => prop.key.name !== 'intl');
  });

  // 5. Modify functional components to remove intl param
  console.log('Removng `intl` from components params');
  root.find(j.VariableDeclarator, {
    init: (init) => j.ArrowFunctionExpression.check(init)
      && (j.BlockStatement.check(init.body) || j.JSXElement.check(init.body)),
  }).forEach((path) => {
    const fn = path.node.init;
    const hasIntlParam = fn.params.length && fn.params[0].type === 'ObjectPattern';
    if (hasIntlParam) {
      fn.params[0].properties = fn.params[0].properties.filter((p) => p.key.name !== 'intl');
      removedIntlParam = true;
      if (fn.params[0].properties.length === 0) {
        fn.params = [];
      }
    }
    const isIntlWrappedComponent = componentsWithInjectIntl.includes(path.value.id.name);
    if (isIntlWrappedComponent && intlUsed) {
      const intlDeclaration = j.variableDeclaration('const', [
        j.variableDeclarator(
          j.identifier('intl'),
          j.callExpression(j.identifier(USE_INTL), []),
        ),
      ]);

      if (j.JSXElement.check(fn.body)) {
        fn.body = j.blockStatement([
          intlDeclaration,
          j.returnStatement(fn.body),
        ]);
      } else if (j.BlockStatement.check(fn.body)) {
        fn.body.body.unshift(intlDeclaration);
      }
    }
  });

  // 6. Replace injectIntl(Component) with just Component
  console.log('Replacing injectIntl(Component) with just Component...');
  if (injectIntlImported) {
    root.find(j.ExportDefaultDeclaration).forEach((path) => {
      const expr = path.node.declaration;
      if (
        j.CallExpression.check(expr)
        && expr.callee.name === INJECT_INTL
        && expr.arguments.length === 1
      ) {
        path.node.declaration = expr.arguments[0];
      }

      // Handles nested HOCs like injectIntl(connect(...)(Component))
      if (
        j.CallExpression.check(expr)
        && j.CallExpression.check(expr.callee)
        && expr.callee.callee?.name === INJECT_INTL
      ) {
        expr.callee = expr.callee.arguments[0];
      }
    });
  }
  console.log('Done!');
  // eslint-disable-next-line consistent-return
  return root.toSource({ quote: 'single', trailingComma: true });
};
