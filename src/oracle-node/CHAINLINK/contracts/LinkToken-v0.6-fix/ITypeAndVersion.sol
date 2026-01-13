// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// @dev Interface contracts should use to report its type and version.
interface ITypeAndVersion {
  /**
   * @dev Returns type and version for the contract.
   *
   * The returned string has the following format: <contract name><SPACE><semver>
   * Try to keep its length less than 32 to take up less contract space.
   */
  function typeAndVersion()
    external
    pure
    returns (string memory);
}
