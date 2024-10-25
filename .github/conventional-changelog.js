'use strict'
const config = require('conventional-changelog-conventionalcommits');

module.exports = config({
    "types": [
        {"type": "feat", "section": "Features"},
        {"type": "fix", "section": "Bug Fixes"},
        {"type": "docs", "section": "Documentation"},
        {"type": "chore", "section": "Other Changes"},
        {"type": "style", "section": "Other Changes"},
        {"type": "refactor", "section": "Other Changes"},
        {"type": "perf", "section": "Other Changes"},
        {"type": "test", "section": "Other Changes"}
    ]
})
