import inherits from 'inherits';
import CommandInterceptor from 'diagram-js/lib/command/CommandInterceptor';
import { is } from 'bpmn-js/lib/util/ModelUtil';
import { add as collectionAdd, remove as collectionRemove } from 'diagram-js/lib/util/Collections';
import {
  getAssetData,
  getAssetOperationData,
  isAssetElement,
  isChoreographyTask,
  updateAssetOperation,
} from '../../../../utils/assetExtension';

export default function DataAssociationBehavior(injector) {
  injector.invoke(CommandInterceptor, this);

  const elementRegistry = injector.get('elementRegistry');
  const modeling = injector.get('modeling');
  const moddle = injector.get('moddle');
  const canvas = injector.get('canvas');
  const eventBus = injector.get('eventBus');
  const connectionDocking = injector.get('connectionDocking');

  eventBus.on('import.done', function() {
    setTimeout(function() {
      restoreMissingAssetReferenceConnections();
      syncAllAssetOperationRefs();
      updateAllAssetReferenceLabels();
    }, 0);
  });

  eventBus.on('saveXML.start', function() {
    syncAllAssetOperationRefs();
  });

  this.postExecuted('connection.create', function(event) {
    ensureAssetReferenceDirection(event.context.connection);
    relayoutAssetReferenceConnection(event.context.connection);
    syncRefsAroundConnection(event.context.connection);
    updateAssetReferenceLabel(event.context.connection);
  });

  this.postExecuted('connection.reconnect', function(event) {
    ensureAssetReferenceDirection(event.context.connection);
    relayoutAssetReferenceConnection(event.context.connection);
    syncRefsAroundConnection(event.context.connection);
    updateAssetReferenceLabel(event.context.connection);
  });

  this.postExecuted('shape.move', function(event) {
    const shape = event.context.shape;
    scheduleRelayoutAssetReferenceConnections(getAssetReferenceConnectionsForShape(shape));
  });

  this.postExecuted('elements.move', function(event) {
    const shapes = event.context.shapes || [];
    const connections = [];
    shapes.forEach(shape => {
      connections.push(...getAssetReferenceConnectionsForShape(shape));
    });
    scheduleRelayoutAssetReferenceConnections(connections);
  });

  this.postExecuted('connection.delete', function(event) {
    const connection = event.context.connection;
    [connection.source, connection.target, event.context.oldSource, event.context.oldTarget]
      .filter(isChoreographyTask)
      .forEach(syncAssetOperationRefsForTask);
  });

  this.postExecuted('element.updateProperties', function(event) {
    const element = event.context.element;
    if (isChoreographyTask(element)) {
      syncAssetOperationRefsForTask(element);
      updateConnectionLabelsForTask(element);
    }
    if (isAssetElement(element)) {
      updateConnectionLabelsForAsset(element);
    }
  });

  this.postExecuted('element.updateModdleProperties', function(event) {
    const element = event.context.element;
    if (isChoreographyTask(element)) {
      syncAssetOperationRefsForTask(element);
      updateConnectionLabelsForTask(element);
    }
  });

  function syncAllAssetOperationRefs() {
    elementRegistry.getAll().forEach(element => {
      if (isChoreographyTask(element)) {
        syncAssetOperationRefsForTask(element);
      }
    });
  }

  function restoreMissingAssetReferenceConnections() {
    elementRegistry.getAll().forEach(taskElement => {
      if (!isChoreographyTask(taskElement)) return;

      const data = getAssetOperationData(taskElement);
      data.inputAssetRefs.forEach(assetId => {
        const assetElement = elementRegistry.get(assetId);
        if (assetElement && !hasAssetReferenceConnection(assetElement, taskElement)) {
          modeling.connect(assetElement, taskElement, {
            type: 'bpmn:Association',
            associationDirection: 'One'
          });
        }
      });

      data.outputAssetRefs.forEach(assetId => {
        const assetElement = elementRegistry.get(assetId);
        if (assetElement && !hasAssetReferenceConnection(taskElement, assetElement)) {
          modeling.connect(taskElement, assetElement, {
            type: 'bpmn:Association',
            associationDirection: 'One'
          });
        }
      });
    });
  }

  function ensureAssetReferenceDirection(connection) {
    if (!isAssetReferenceConnection(connection)) return;
    if (connection.businessObject.associationDirection !== 'One') {
      modeling.updateProperties(connection, {
        associationDirection: 'One'
      });
    }
  }

  function relayoutAssetReferenceConnection(connection) {
    if (!isAssetReferenceConnection(connection)) return;
    const source = connection.source;
    const target = connection.target;
    if (!source || !target) return;

    const centerWaypoints = [
      getElementCenter(source),
      getElementCenter(target)
    ];

    let waypoints = centerWaypoints;
    const oldWaypoints = connection.waypoints;
    try {
      connection.waypoints = centerWaypoints;
      waypoints = connectionDocking.getCroppedWaypoints(connection, source, target);
    } catch {
      // Fall back to center points if the custom shape path cannot be cropped.
    } finally {
      connection.waypoints = oldWaypoints;
    }

    connection.hidden = false;
    connection.waypoints = waypoints;
    moveConnectionToRoot(connection);
    eventBus.fire('element.changed', { element: connection });
  }

  function getAssetReferenceConnectionsForShape(shape) {
    return [...(shape.incoming || []), ...(shape.outgoing || [])]
      .filter(isAssetReferenceConnection);
  }

  function scheduleRelayoutAssetReferenceConnections(connections) {
    const uniqueConnections = Array.from(new Set(connections || []));
    if (!uniqueConnections.length) return;

    setTimeout(function() {
      uniqueConnections.forEach(connection => {
        if (!isAssetReferenceConnection(connection)) return;
        relayoutAssetReferenceConnection(connection);
        updateAssetReferenceLabel(connection);
      });
    }, 0);
  }

  function moveConnectionToRoot(connection) {
    const root = canvas.getRootElement();
    if (!root || connection.parent === root) return;

    collectionRemove(connection.parent && connection.parent.children, connection);
    collectionAdd(root.children, connection);
    connection.parent = root;
  }

  function syncRefsAroundConnection(connection) {
    if (!isAssetReferenceConnection(connection)) return;
    if (isChoreographyTask(connection.source)) {
      syncAssetOperationRefsForTask(connection.source);
    }
    if (isChoreographyTask(connection.target)) {
      syncAssetOperationRefsForTask(connection.target);
    }
  }

  function syncAssetOperationRefsForTask(taskElement) {
    if (!taskElement || !isChoreographyTask(taskElement)) return;

    const inputAssetRefs = [];
    const outputAssetRefs = [];

    (taskElement.incoming || []).forEach(connection => {
      if (isAssetReferenceConnection(connection) && isAssetElement(connection.source)) {
        inputAssetRefs.push(connection.source.id);
      }
    });

    (taskElement.outgoing || []).forEach(connection => {
      if (isAssetReferenceConnection(connection) && isAssetElement(connection.target)) {
        outputAssetRefs.push(connection.target.id);
      }
    });

    const data = getAssetOperationData(taskElement);
    const sameInputs = refsEqual(data.inputAssetRefs, inputAssetRefs);
    const sameOutputs = refsEqual(data.outputAssetRefs, outputAssetRefs);
    if (sameInputs && sameOutputs) return;

    updateAssetOperation(taskElement, moddle, modeling, {
      ...data,
      inputAssetRefs,
      outputAssetRefs,
    });
  }

  function updateAllAssetReferenceLabels() {
    elementRegistry.getAll().forEach(element => {
      if (isAssetReferenceConnection(element)) {
        updateAssetReferenceLabel(element);
      }
    });
  }

  function updateConnectionLabelsForTask(taskElement) {
    [...(taskElement.incoming || []), ...(taskElement.outgoing || [])].forEach(updateAssetReferenceLabel);
  }

  function updateConnectionLabelsForAsset(assetElement) {
    [...(assetElement.incoming || []), ...(assetElement.outgoing || [])].forEach(updateAssetReferenceLabel);
  }

  function updateAssetReferenceLabel(connection) {
    if (!isAssetReferenceConnection(connection)) return;

    const source = connection.source;
    const target = connection.target;
    const isInput = isAssetElement(source) && isChoreographyTask(target);
    if (!isInput) {
      createOrUpdateConnectionLabel(connection, '');
      styleAssetReferenceConnection(connection);
      return;
    }

    const asset = getAssetData(source);
    const operation = getAssetOperationData(target).operation;
    const label = asset.assetType === 'distributive' &&
      ['grant usage rights', 'revoke usage rights'].includes(operation)
      ? 'use'
      : '';

    if ((connection.businessObject.name || '') !== label) {
      modeling.updateProperties(connection, { name: label });
    }
    styleAssetReferenceConnection(connection);
    createOrUpdateConnectionLabel(connection, label);
  }

  function styleAssetReferenceConnection(connection) {
    try {
      const gfx = canvas.getGraphics(connection);
      if (!gfx) return;

      const path = gfx.querySelector('path');
      if (!path) return;

      path.setAttribute('stroke', '#2f3a45');
      path.setAttribute('stroke-width', '1.6');
      path.setAttribute('stroke-dasharray', '4,4');
      path.setAttribute('stroke-linecap', 'round');
      path.setAttribute('stroke-linejoin', 'round');
    } catch {
      // Styling is best-effort; refs remain the source of truth.
    }
  }

  function createOrUpdateConnectionLabel(connection, labelText) {
    try {
      const gfx = canvas.getGraphics(connection);
      if (!gfx) return;

      const existingLabel = gfx.querySelector('.choreo-connection-label');
      const existingBg = gfx.querySelector('.choreo-connection-label-bg');
      if (existingLabel) existingLabel.remove();
      if (existingBg) existingBg.remove();
      if (!labelText) return;

      const waypoints = connection.waypoints || [];
      if (waypoints.length < 2) return;

      const start = waypoints[0];
      const end = waypoints[waypoints.length - 1];
      const midPoint = {
        x: (start.x + end.x) / 2,
        y: (start.y + end.y) / 2,
      };

      const svgNS = 'http://www.w3.org/2000/svg';
      const text = document.createElementNS(svgNS, 'text');
      text.setAttribute('class', 'choreo-connection-label djs-label');
      text.setAttribute('x', String(midPoint.x));
      text.setAttribute('y', String(midPoint.y - 5));
      text.setAttribute('text-anchor', 'middle');
      text.setAttribute('font-family', 'Arial, sans-serif');
      text.setAttribute('font-size', '11px');
      text.setAttribute('fill', '#000');
      text.setAttribute('font-weight', 'bold');
      text.textContent = labelText;

      const rect = document.createElementNS(svgNS, 'rect');
      rect.setAttribute('class', 'choreo-connection-label-bg');
      rect.setAttribute('fill', 'white');
      rect.setAttribute('opacity', '0.8');

      gfx.appendChild(text);
      const bbox = text.getBBox();
      rect.setAttribute('x', String(bbox.x - 2));
      rect.setAttribute('y', String(bbox.y - 1));
      rect.setAttribute('width', String(bbox.width + 4));
      rect.setAttribute('height', String(bbox.height + 2));
      rect.setAttribute('rx', '2');
      gfx.insertBefore(rect, text);
    } catch {
      // Visual labels are best-effort; refs remain the source of truth.
    }
  }
}

function hasAssetReferenceConnection(source, target) {
  return (source.outgoing || []).some(connection => {
    return isAssetReferenceConnection(connection) &&
      connection.source === source &&
      connection.target === target;
  });
}

function getElementCenter(element) {
  return {
    x: element.x + element.width / 2,
    y: element.y + element.height / 2
  };
}

function isAssetReferenceConnection(connection) {
  return connection &&
    is(connection, 'bpmn:Association') &&
    (
      isAssetElement(connection.source) && isChoreographyTask(connection.target) ||
      isChoreographyTask(connection.source) && isAssetElement(connection.target)
    );
}

function refsEqual(left, right) {
  const leftSorted = Array.from(new Set(left || [])).sort();
  const rightSorted = Array.from(new Set(right || [])).sort();
  return leftSorted.length === rightSorted.length &&
    leftSorted.every((item, index) => item === rightSorted[index]);
}

DataAssociationBehavior.$inject = ['injector'];
inherits(DataAssociationBehavior, CommandInterceptor);
