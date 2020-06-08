// Copyright (c) 2019 Baldur Karlsson
//
// SPDX-License-Identifier: Apache-2.0

var lunr = require('lunr'),
    stdin = process.stdin,
    stdout = process.stdout,
    buffer = []

stdin.resume()
stdin.setEncoding('utf8')

stdin.on('data', function (data) {
  buffer.push(data)
})

stdin.on('end', function () {
  var documents = JSON.parse(buffer.join(''))

  var idx = lunr(function () {
    this.ref('id')
    this.field('title')
    this.field('body')

    documents.forEach(function (doc) {
      this.add(doc)
    }, this)
  })

  stdout.write("var searchindex = " + JSON.stringify(idx) + ";\n")

  var searchlookup = {};

  for(var i=0; i < documents.length; i++) {
    searchlookup[documents[i].id] = documents[i].title;
  }

  stdout.write("var searchlookup = " + JSON.stringify(searchlookup) + ";\n")
})
