/*
 * Copyright IBM Corp. All Rights Reserved.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

'use strict';

const stateMachine = require('./lib/chaincode');

module.exports.StateMachine = stateMachine;
module.exports.contracts = [stateMachine];
