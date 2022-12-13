// This file is being synced from WordPress/openverse. Any changes made to it
// here will be overwritten. Please make any necessary edits to these files:
// - https://github.com/WordPress/openverse/blob/main/prettier.config.js.jinja

module.exports = {
  trailingComma: 'es5',
  tabWidth: 2,
  semi: false,
  singleQuote: true,
  overrides: [
    {
      files: '*.yml',
      options: {
        singleQuote: false,
      },
    },
  ],
}
