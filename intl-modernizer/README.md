

# Codemod: Replace `injectIntl` HOC with `useIntl` Hook

This jscodeshift codemod automates migrating React components from using the `injectIntl` higher-order component (HOC) to the modern `useIntl` hook from `@edx/frontend-platform/i18n`.

---

## Features

- Removes `injectIntl` and `intlShape` imports.
- Removes `intl` from component function parameters.
- Removes `intl` from `propTypes` and `defaultProps`.
- Adds `useIntl` import and inserts `const intl = useIntl();` inside component bodies where `intl` is used.
- Preserves other HOCs like `connect()` by removing only the `injectIntl` wrapper.
- Updates default exports wrapped with `injectIntl` to export the base or connected component directly.

---

## How It Works

The codemod performs these transformations:

1. Finds components wrapped with `injectIntl(...)`.
2. Detects if `intl` is used inside components.
3. Adds `useIntl` to imports if `intl` is used.
4. Removes `injectIntl` and `intlShape` imports.
5. Removes `intl` from component destructured parameters.
6. Removes `intl` from `propTypes` and `defaultProps`.
7. Adds `const intl = useIntl();` in component function bodies.
8. Removes `injectIntl` wrapping from default exports.

---

## Example

### Before

```jsx
import React from 'react';
import { injectIntl, intlShape } from '@edx/frontend-platform/i18n';
import { connect } from 'react-redux';
import PropTypes from 'prop-types';

const MyComponent = ({ intl, name }) => (
  <div>{intl.formatMessage({ id: 'hello' })} {name}</div>
);

MyComponent.propTypes = {
  intl: intlShape.isRequired,
  name: PropTypes.string,
};

export default injectIntl(connect(mapState)(MyComponent));
```

### After


```jsx
import React from 'react';
import { useIntl } from '@edx/frontend-platform/i18n';
import { connect } from 'react-redux';
import PropTypes from 'prop-types';

const MyComponent = ({ name }) => {
  const intl = useIntl();

  return (
    <div>{intl.formatMessage({ id: 'hello' })} {name}</div>
  );
};

MyComponent.propTypes = {
  name: PropTypes.string,
};

export default connect(mapState)(MyComponent);

```

---

## Usage

it requires jscodeshift:
```bash
npm i -g jscodeshift
```

Run the codemod with jscodeshift:

```bash
npx jscodeshift -t path/to/intl-modernizer.js path/to/your/codefile.js
```



You can also define a script in your `package.json` to simplify usage:

```json
"scripts": {
  "migrate:intl": "jscodeshift -t scripts/intl-modernizer.js"
}
```

Then run it like this:

```bash
npm run migrate:intl -- src/components/MyComponent.jsx
```


---

## Limitations

- Only supports **function components** (arrow or standard).
- Does **not** transform **class components**.
- Only targets imports from `@edx/frontend-platform/i18n`.
- Only updates `default export` wrappers using `injectIntl(...)`.
- Does not handle deeply nested or aliased usages of `injectIntl`.
- It has some code formatting issues.

---

## License

MIT © Your Name or Your Company

---

Feel free to contribute or report issues!