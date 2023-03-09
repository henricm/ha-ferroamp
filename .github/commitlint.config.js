const Configuration = {

  extends: ['@commitlint/config-conventional'],

  /*
   * Any rules defined here will override rules from @commitlint/config-conventional
   */
  rules: {
    'body-max-line-length': [2, 'always', 200],
  },
};

module.exports = Configuration;
