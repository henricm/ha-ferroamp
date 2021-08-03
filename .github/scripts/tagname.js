exports.preVersionGeneration = (version) => {
  if (process.env.GITHUB_REF !== 'refs/heads/master') {
    return version + '-beta'
  }
  return version
}

exports.preTagGeneration = (tag) => {
  if (process.env.GITHUB_REF !== 'refs/heads/master') {
    return tag + '-beta'
  }
  return tag
}
