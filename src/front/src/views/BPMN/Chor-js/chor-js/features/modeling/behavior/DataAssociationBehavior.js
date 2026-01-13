import inherits from 'inherits';
import CommandInterceptor from 'diagram-js/lib/command/CommandInterceptor';
import { is } from 'bpmn-js/lib/util/ModelUtil';

/**
 * Ensures that ChoreographyActivity elements maintain their integrity
 * when DataAssociation connections are created.
 * Also handles automatic synchronization of refTokenIds for value-added assets.
 * @constructor
 * @param {Injector} injector
 */
export default function DataAssociationBehavior(injector) {
  injector.invoke(CommandInterceptor, this);

  const elementRegistry = injector.get('elementRegistry');
  const modeling = injector.get('modeling');
  const canvas = injector.get('canvas');
  const textRenderer = injector.get('textRenderer');
  const eventBus = injector.get('eventBus');
  const modeler = injector.get('bpmnjs') || window.bpmnjs;

  // Listen for import completion to restore labels
  eventBus.on('import.done', function() {
    console.log('[DataAssociationBehavior] import.done - restoring connection labels');
    restoreAllConnectionLabels();
  });

  // Also restore labels after a short delay to ensure everything is rendered
  eventBus.on('canvas.viewbox.changed', function() {
    // Only run once after import
    if (!restoreAllConnectionLabels.hasRun) {
      restoreAllConnectionLabels.hasRun = true;
      setTimeout(function() {
        restoreAllConnectionLabels();
        restoreAllConnectionLabels.hasRun = false;
      }, 100);
    }
  });

  /**
   * Restore labels for all existing connections in the diagram
   */
  function restoreAllConnectionLabels() {
    const allElements = elementRegistry.getAll();
    console.log('[DataAssociationBehavior] Restoring labels for', allElements.length, 'elements');

    allElements.forEach(function(element) {
      if (is(element, 'bpmn:DataInputAssociation')) {
        const source = element.source;
        const target = element.target;

        if (source && target) {
          // Check if this connection should have a label
          const shouldHaveLabel = checkIfShouldHaveLabel(element, source, target);
          if (shouldHaveLabel) {
            const labelText = element.businessObject.name || 'use';
            console.log('[DataAssociationBehavior] Restoring label for connection:', element.id, 'label:', labelText);
            createOrUpdateConnectionLabel(element, labelText);
          }
        }
      }
    });
  }

  /**
   * Check if a connection should have a "use" label
   */
  function checkIfShouldHaveLabel(connection, source, target) {
    if (!is(connection, 'bpmn:DataInputAssociation')) return false;
    if (!is(source, 'bpmn:DataObjectReference') || !is(target, 'bpmn:Task')) return false;

    // Get asset type from DataObject
    const sourceDocs = source.businessObject.documentation;
    let assetType = null;
    if (Array.isArray(sourceDocs) && sourceDocs.length) {
      try {
        const parsed = JSON.parse(sourceDocs[0].text);
        assetType = parsed.assetType;
      } catch {
        // ignore
      }
    }

    // Get operation from Task
    const targetDocs = target.businessObject.documentation;
    let operation = null;
    if (Array.isArray(targetDocs) && targetDocs.length) {
      try {
        const parsed = JSON.parse(targetDocs[0].text);
        operation = parsed.operation;
      } catch {
        // ignore
      }
    }

    return assetType === 'distributive' && operation && ['grant usage rights', 'revoke usage rights'].includes(operation);
  }

  // Protect ChoreographyActivity AFTER creating DataAssociation connections
  this.postExecuted('connection.create', function (event) {
    const context = event.context;
    const connection = context.connection;
    const source = context.source;
    const target = context.target;

    // If a DataAssociation is connected to/from a ChoreographyActivity,
    // ensure the activity maintains its proper structure
    if (is(connection, 'bpmn:DataAssociation')) {
      console.log('[DataAssociationBehavior] postExecuted connection.create:');
      console.log('  Connection type:', connection.businessObject.$type);

      const connectionBo = connection.businessObject;
      const activityBo = getChoreographyActivity(source, target);
      if (activityBo) {
        connectionBo.$parent = activityBo;
        if (is(connectionBo, 'bpmn:DataInputAssociation')) {
          if (!connectionBo.sourceRef && source) {
            connectionBo.sourceRef = [source.businessObject];
          }
          if (!activityBo.dataInputAssociations) {
            activityBo.dataInputAssociations = [];
          }
          if (!activityBo.dataInputAssociations.includes(connectionBo)) {
            activityBo.dataInputAssociations.push(connectionBo);
          }
        } else if (is(connectionBo, 'bpmn:DataOutputAssociation')) {
          if (!connectionBo.targetRef && target) {
            connectionBo.targetRef = target.businessObject;
          }
          if (!activityBo.dataOutputAssociations) {
            activityBo.dataOutputAssociations = [];
          }
          if (!activityBo.dataOutputAssociations.includes(connectionBo)) {
            activityBo.dataOutputAssociations.push(connectionBo);
          }
        }

        if (activityBo.$parent && activityBo.$parent.flowElements) {
          const idx = activityBo.$parent.flowElements.indexOf(connectionBo);
          if (idx !== -1) {
            activityBo.$parent.flowElements.splice(idx, 1);
          }
        }
      }

      if (is(source, 'bpmn:ChoreographyActivity')) {
        console.log('  Source BEFORE ensure:', source.type, source.businessObject.$type);
        console.log('  Source bandShapes BEFORE:', source.bandShapes?.length);
        ensureChoreographyActivity(source);
        console.log('  Source AFTER ensure:', source.type, source.businessObject.$type);
        console.log('  Source bandShapes AFTER:', source.bandShapes?.length);
      }
      if (is(target, 'bpmn:ChoreographyActivity')) {
        console.log('  Target BEFORE ensure:', target.type, target.businessObject.$type);
        console.log('  Target bandShapes BEFORE:', target.bandShapes?.length);
        ensureChoreographyActivity(target);
        console.log('  Target AFTER ensure:', target.type, target.businessObject.$type);
        console.log('  Target bandShapes AFTER:', target.bandShapes?.length);
      }

      // Auto-sync refTokenIds for value-added branch/merge operations
      syncRefTokenIdsForTask(target);

      // Add "use" label for distributive assets with grant/revoke usage rights
      addUseLabelForDistributive(connection, source, target);
    }
  });

  // Also protect when reconnecting
  this.postExecuted('connection.reconnect', function (event) {
    const context = event.context;
    const connection = context.connection;
    const source = context.newSource || context.source;
    const target = context.newTarget || context.target;

    if (is(connection, 'bpmn:DataAssociation')) {
      if (is(source, 'bpmn:ChoreographyActivity')) {
        ensureChoreographyActivity(source);
      }
      if (is(target, 'bpmn:ChoreographyActivity')) {
        ensureChoreographyActivity(target);
      }

      // Auto-sync refTokenIds for value-added branch/merge operations
      syncRefTokenIdsForTask(target);

      // Add "use" label for distributive assets with grant/revoke usage rights
      addUseLabelForDistributive(connection, source, target);
    }
  });

  // Listen for connection deletion and update refTokenIds
  this.postExecuted('connection.delete', function (event) {
    const context = event.context;
    const connection = context.connection;
    const target = connection.target;

    if (is(connection, 'bpmn:DataInputAssociation') && is(target, 'bpmn:Task')) {
      // Auto-sync refTokenIds for value-added branch/merge operations
      syncRefTokenIdsForTask(target);
    }
  });

  // Listen for connection layout changes (waypoints update)
  this.postExecuted('connection.layout', function (event) {
    const context = event.context;
    const connection = context.connection;

    if (is(connection, 'bpmn:DataInputAssociation')) {
      const source = connection.source;
      const target = connection.target;

      if (source && target) {
        const shouldHaveLabel = checkIfShouldHaveLabel(connection, source, target);
        if (shouldHaveLabel) {
          const labelText = connection.businessObject.name || 'use';
          console.log('[DataAssociationBehavior] Connection layout changed, updating label');
          createOrUpdateConnectionLabel(connection, labelText);
        }
      }
    }
  });

  // Listen for connection waypoint updates
  this.postExecuted('connection.updateWaypoints', function (event) {
    const context = event.context;
    const connection = context.connection;

    if (is(connection, 'bpmn:DataInputAssociation')) {
      const source = connection.source;
      const target = connection.target;

      if (source && target) {
        const shouldHaveLabel = checkIfShouldHaveLabel(connection, source, target);
        if (shouldHaveLabel) {
          const labelText = connection.businessObject.name || 'use';
          console.log('[DataAssociationBehavior] Connection waypoints updated, updating label');
          createOrUpdateConnectionLabel(connection, labelText);
        }
      }
    }
  });

  // Listen for element property changes (e.g., tokenId changes)
  this.postExecuted('element.updateProperties', function (event) {
    const context = event.context;
    const element = context.element;

    // If a DataObject's properties changed, sync all Tasks that reference it
    if (is(element, 'bpmn:DataObjectReference')) {
      syncAllTasksReferencingDataObject(element);
      // Also update connection labels for all outgoing connections
      updateConnectionLabelsForDataObject(element);
    }

    // If a Task's properties changed, update connection labels
    if (is(element, 'bpmn:Task')) {
      updateConnectionLabelsForTask(element);
    }
  });

  /**
   * Sync refTokenIds for a Task (if it's a value-added branch/merge operation)
   */
  function syncRefTokenIdsForTask(taskElement) {
    if (!taskElement || !is(taskElement, 'bpmn:Task')) return;

    const taskDocs = taskElement.businessObject.documentation;
    if (!Array.isArray(taskDocs) || !taskDocs.length) return;

    try {
      const taskData = JSON.parse(taskDocs[0].text);
      if (!taskData.operation || !['branch', 'merge'].includes(taskData.operation)) return;

      // Get the output DataObject
      const outgoing = taskElement.outgoing || [];
      for (const connection of outgoing) {
        const connBo = connection.businessObject;
        if (is(connBo, 'bpmn:DataOutputAssociation')) {
          const dataObjectElement = connection.target;

          if (dataObjectElement && is(dataObjectElement, 'bpmn:DataObjectReference')) {
            const dataDocs = dataObjectElement.businessObject.documentation;
            if (Array.isArray(dataDocs) && dataDocs.length) {
              try {
                const dataObjectData = JSON.parse(dataDocs[0].text);
                if (dataObjectData.assetType !== 'value-added') continue;

                // Collect tokenIds from all input DataObjects
                const incomingTokenIds = [];
                const incoming = taskElement.incoming || [];
                for (const inConn of incoming) {
                  const inConnBo = inConn.businessObject;
                  if (is(inConnBo, 'bpmn:DataInputAssociation')) {
                    const inDataObject = inConn.source;
                    if (inDataObject && is(inDataObject, 'bpmn:DataObjectReference')) {
                      const inDocs = inDataObject.businessObject.documentation;
                      if (Array.isArray(inDocs) && inDocs.length) {
                        try {
                          const inData = JSON.parse(inDocs[0].text);
                          if (inData.tokenId) {
                            incomingTokenIds.push(inData.tokenId);
                          }
                        } catch {
                          // ignore
                        }
                      }
                    }
                  }
                }

                // Update refTokenIds in output DataObject
                dataObjectData.refTokenIds = incomingTokenIds;

                const modeling = injector.get('modeling');
                modeling.updateProperties(dataObjectElement, {
                  documentation: [
                    modeler._moddle.create('bpmn:Documentation', {
                      text: JSON.stringify(dataObjectData, null, 2),
                    }),
                  ],
                });
              } catch {
                // ignore
              }
            }
          }
        }
      }
    } catch {
      // ignore
    }
  }

  /**
   * Sync all Tasks that have incoming connections from the given DataObject
   */
  function syncAllTasksReferencingDataObject(dataObjectElement) {
    if (!dataObjectElement || !is(dataObjectElement, 'bpmn:DataObjectReference')) return;

    const outgoing = dataObjectElement.outgoing || [];
    for (const connection of outgoing) {
      const connBo = connection.businessObject;
      if (is(connBo, 'bpmn:DataInputAssociation')) {
        const taskElement = connection.target;
        if (taskElement && is(taskElement, 'bpmn:Task')) {
          syncRefTokenIdsForTask(taskElement);
        }
      }
    }
  }

  /**
   * Add "use" label for distributive assets with grant/revoke usage rights
   */
  function addUseLabelForDistributive(connection, source, target) {
    console.log('[DataAssociationBehavior] addUseLabelForDistributive called');
    console.log('  Connection type:', connection?.businessObject?.$type);
    console.log('  Source type:', source?.type, 'Target type:', target?.type);

    // Only handle DataInputAssociation (DataObject -> Task)
    if (!is(connection, 'bpmn:DataInputAssociation')) {
      console.log('  -> Not a DataInputAssociation, skipping');
      return;
    }
    if (!is(source, 'bpmn:DataObjectReference') || !is(target, 'bpmn:Task')) {
      console.log('  -> Source is not DataObject or target is not Task, skipping');
      return;
    }

    // Get asset type from DataObject
    const sourceDocs = source.businessObject.documentation;
    let assetType = null;
    if (Array.isArray(sourceDocs) && sourceDocs.length) {
      try {
        const parsed = JSON.parse(sourceDocs[0].text);
        assetType = parsed.assetType;
      } catch {
        // ignore
      }
    }
    console.log('  Asset type from DataObject:', assetType);

    // Get operation from Task
    const targetDocs = target.businessObject.documentation;
    let operation = null;
    if (Array.isArray(targetDocs) && targetDocs.length) {
      try {
        const parsed = JSON.parse(targetDocs[0].text);
        operation = parsed.operation;
      } catch {
        // ignore
      }
    }
    console.log('  Operation from Task:', operation);

    // Determine the new label value
    const shouldHaveLabel = assetType === 'distributive' && operation && ['grant usage rights', 'revoke usage rights'].includes(operation);
    const newLabel = shouldHaveLabel ? 'use' : '';
    const currentLabel = connection.businessObject.name || '';

    console.log('  Should have label:', shouldHaveLabel);
    console.log('  New label:', newLabel || '(empty)');
    console.log('  Current label:', currentLabel || '(empty)');

    // Only update if the label actually changed
    if (currentLabel !== newLabel) {
      // Set the name property on the businessObject
      connection.businessObject.name = newLabel;

      // Update via modeling to trigger events
      modeling.updateProperties(connection, {
        name: newLabel
      });

      // Create or update visual label on the SVG
      createOrUpdateConnectionLabel(connection, newLabel);

      console.log('[DataAssociationBehavior] ✓ Successfully updated connection label to:', newLabel || '(empty)');
    } else {
      console.log('  -> Label unchanged, skipping update');
    }
  }

  /**
   * Create or update visual label on a connection
   */
  function createOrUpdateConnectionLabel(connection, labelText) {
    try {
      // Get the graphical element for the connection
      const gfx = canvas.getGraphics(connection);
      if (!gfx) {
        console.log('[DataAssociationBehavior] No graphics found for connection');
        return;
      }

      // Remove existing custom label if any
      const existingLabel = gfx.querySelector('.choreo-connection-label');
      if (existingLabel) {
        existingLabel.remove();
      }

      // If label text is empty, we're done
      if (!labelText) {
        return;
      }

      // Calculate the midpoint of the connection (geometric center)
      const waypoints = connection.waypoints || [];
      if (waypoints.length < 2) {
        console.log('[DataAssociationBehavior] Connection has no waypoints');
        return;
      }

      // Calculate total length of the connection
      let totalLength = 0;
      const segmentLengths = [];
      for (let i = 0; i < waypoints.length - 1; i++) {
        const p1 = waypoints[i];
        const p2 = waypoints[i + 1];
        const length = Math.sqrt(Math.pow(p2.x - p1.x, 2) + Math.pow(p2.y - p1.y, 2));
        segmentLengths.push(length);
        totalLength += length;
      }

      // Find the point at half the total length
      const halfLength = totalLength / 2;
      let accumulatedLength = 0;
      let midPoint = { x: 0, y: 0 };

      for (let i = 0; i < segmentLengths.length; i++) {
        if (accumulatedLength + segmentLengths[i] >= halfLength) {
          // The midpoint is on this segment
          const remainingLength = halfLength - accumulatedLength;
          const ratio = remainingLength / segmentLengths[i];
          const p1 = waypoints[i];
          const p2 = waypoints[i + 1];
          midPoint = {
            x: p1.x + (p2.x - p1.x) * ratio,
            y: p1.y + (p2.y - p1.y) * ratio
          };
          break;
        }
        accumulatedLength += segmentLengths[i];
      }

      // Create SVG text element
      const svgNS = 'http://www.w3.org/2000/svg';
      const text = document.createElementNS(svgNS, 'text');
      text.setAttribute('class', 'choreo-connection-label djs-label');
      text.setAttribute('x', midPoint.x);
      text.setAttribute('y', midPoint.y - 5); // Offset above the line
      text.setAttribute('text-anchor', 'middle');
      text.setAttribute('font-family', 'Arial, sans-serif');
      text.setAttribute('font-size', '11px');
      text.setAttribute('fill', '#000');
      text.setAttribute('font-weight', 'bold');
      text.textContent = labelText;

      // Create a white background for better readability
      const rect = document.createElementNS(svgNS, 'rect');
      rect.setAttribute('class', 'choreo-connection-label-bg');
      rect.setAttribute('fill', 'white');
      rect.setAttribute('opacity', '0.8');

      // Get text dimensions and position background
      gfx.appendChild(text);
      const bbox = text.getBBox();
      rect.setAttribute('x', bbox.x - 2);
      rect.setAttribute('y', bbox.y - 1);
      rect.setAttribute('width', bbox.width + 4);
      rect.setAttribute('height', bbox.height + 2);
      rect.setAttribute('rx', '2');

      // Insert background before text
      gfx.insertBefore(rect, text);

      console.log('[DataAssociationBehavior] Created visual label on connection at', midPoint);
    } catch (error) {
      console.error('[DataAssociationBehavior] Error creating visual label:', error);
    }
  }

  /**
   * Update connection labels for all outgoing connections from a DataObject
   */
  function updateConnectionLabelsForDataObject(dataObjectElement) {
    if (!dataObjectElement || !is(dataObjectElement, 'bpmn:DataObjectReference')) return;

    const outgoing = dataObjectElement.outgoing || [];
    for (const connection of outgoing) {
      if (is(connection, 'bpmn:DataInputAssociation')) {
        const taskElement = connection.target;
        if (taskElement && is(taskElement, 'bpmn:Task')) {
          addUseLabelForDistributive(connection, dataObjectElement, taskElement);
        }
      }
    }
  }

  /**
   * Update connection labels for all incoming connections to a Task
   */
  function updateConnectionLabelsForTask(taskElement) {
    if (!taskElement || !is(taskElement, 'bpmn:Task')) return;

    const incoming = taskElement.incoming || [];
    for (const connection of incoming) {
      if (is(connection, 'bpmn:DataInputAssociation')) {
        const dataObjectElement = connection.source;
        if (dataObjectElement && is(dataObjectElement, 'bpmn:DataObjectReference')) {
          addUseLabelForDistributive(connection, dataObjectElement, taskElement);
        }
      }
    }
  }
}

function ensureChoreographyActivity(shape) {
  const businessObject = shape.businessObject;

  // Ensure the shape maintains its ChoreographyActivity properties
  if (is(businessObject, 'bpmn:ChoreographyActivity')) {
    // Make sure participantRef array exists
    if (!businessObject.participantRef) {
      businessObject.participantRef = [];
    }

    // Make sure bandShapes array exists
    if (!shape.bandShapes) {
      shape.bandShapes = [];
    }
  }
}

function getChoreographyActivity(source, target) {
  if (is(source, 'bpmn:ChoreographyActivity')) {
    return source.businessObject;
  }
  if (is(target, 'bpmn:ChoreographyActivity')) {
    return target.businessObject;
  }
  return null;
}

DataAssociationBehavior.$inject = ['injector'];
inherits(DataAssociationBehavior, CommandInterceptor);