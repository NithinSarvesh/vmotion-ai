import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import type { ClusterState, Recommendation, MigrationTaskStatus } from '../types';

interface HeroCluster3DProps {
  cluster: ClusterState | null;
  recommendation?: Recommendation | null;
  activeTasks?: MigrationTaskStatus[];
  onSelectNode?: (nodeId: string) => void;
  onSelectVm?: (vmId: string) => void;
}

export const HeroCluster3D: React.FC<HeroCluster3DProps> = ({
  cluster,
  recommendation,
  activeTasks = [],
  onSelectNode,
  onSelectVm,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [hoveredEntity, setHoveredEntity] = useState<{
    type: 'node' | 'vm' | 'ai_core';
    id: string;
    label: string;
    metric?: string;
    x: number;
    y: number;
  } | null>(null);

  // Active or recommended migration
  const activeTask = activeTasks.length > 0 ? activeTasks[0] : null;
  const isMigrating = Boolean(
    activeTask ||
    (recommendation && recommendation.action_type === 'MIGRATE' && recommendation.vm_id && recommendation.target_node)
  );

  const sourceNodeId = activeTask?.source_node || recommendation?.source_node || 'pve-node-1';
  const targetNodeId = activeTask?.target_node || recommendation?.target_node || 'pve-node-2';
  const migratingVmId = activeTask?.vm_id || recommendation?.vm_id || 'vm-101';

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const width = container.clientWidth;
    const height = container.clientHeight || 520;

    // Check reduced motion preference
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // --- Scene, Camera, Renderer ---
    const scene = new THREE.Scene();
    scene.background = null; // transparent to blend with light page background

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.set(0, 3.2, 10.5);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(width, height);
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.1;
    container.appendChild(renderer.domElement);

    // --- Lighting ---
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.85);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xffffff, 1.2);
    dirLight.position.set(5, 10, 7);
    scene.add(dirLight);

    const blueLight = new THREE.PointLight(0x2563eb, 2.5, 20);
    blueLight.position.set(0, 1, 3);
    scene.add(blueLight);

    const cyanLight = new THREE.PointLight(0x0284c7, 1.8, 18);
    cyanLight.position.set(-4, -1, 2);
    scene.add(cyanLight);

    // --- Node Positions ---
    const nodeCoords: Record<string, THREE.Vector3> = {
      'node-01': new THREE.Vector3(-3.2, 0.8, 0),
      'node-02': new THREE.Vector3(3.2, 0.8, 0),
      'node-03': new THREE.Vector3(0, -2.0, 0.5),
      'pve-node-1': new THREE.Vector3(-3.2, 0.8, 0),
      'pve-node-2': new THREE.Vector3(3.2, 0.8, 0),
      'pve-node-3': new THREE.Vector3(0, -2.0, 0.5),
    };

    const fallbackNodes = ['node-01', 'node-02', 'node-03'];
    const nodesList = cluster && Object.keys(cluster.nodes).length > 0
      ? Object.keys(cluster.nodes).slice(0, 3)
      : fallbackNodes;

    // Normalized node map to 3 positions
    const activeNodePos: Record<string, THREE.Vector3> = {};
    const defaultPositions = [
      new THREE.Vector3(-3.4, 0.9, 0),
      new THREE.Vector3(3.4, 0.9, 0),
      new THREE.Vector3(0, -2.2, 0.6)
    ];

    nodesList.forEach((nid, i) => {
      activeNodePos[nid] = nodeCoords[nid] || defaultPositions[i % 3];
    });

    // Group holding all interactive objects
    const clusterGroup = new THREE.Group();
    scene.add(clusterGroup);

    // --- 1. AI Decision Core ---
    const coreGroup = new THREE.Group();
    coreGroup.position.set(0, 0.6, 0);

    const coreGeo = new THREE.IcosahedronGeometry(0.75, 1);
    const coreMat = new THREE.MeshStandardMaterial({
      color: 0x2563eb,
      roughness: 0.2,
      metalness: 0.7,
      wireframe: false,
    });
    const coreMesh = new THREE.Mesh(coreGeo, coreMat);
    (coreMesh as any).meta = { type: 'ai_core', id: 'ai-core', label: 'PPO V5 NEURAL CORE', metric: '103-dim state vector' };
    coreGroup.add(coreMesh);

    // Outer Wireframe Cage
    const wireGeo = new THREE.IcosahedronGeometry(0.95, 1);
    const wireMat = new THREE.MeshBasicMaterial({
      color: 0x7c3aed,
      wireframe: true,
      transparent: true,
      opacity: 0.35,
    });
    const wireMesh = new THREE.Mesh(wireGeo, wireMat);
    coreGroup.add(wireMesh);

    // Subtle orbital ring
    const ringGeo = new THREE.TorusGeometry(1.2, 0.015, 16, 64);
    const ringMat = new THREE.MeshBasicMaterial({
      color: 0x0284c7,
      transparent: true,
      opacity: 0.45,
    });
    const ringMesh = new THREE.Mesh(ringGeo, ringMat);
    ringMesh.rotation.x = Math.PI / 3;
    coreGroup.add(ringMesh);

    clusterGroup.add(coreGroup);

    // --- 2. Compute Nodes ---
    const interactableObjects: THREE.Object3D[] = [coreMesh];
    const nodePedestals: THREE.Mesh[] = [];

    nodesList.forEach((nodeId) => {
      const pos = activeNodePos[nodeId];
      const nodeTelemetry = cluster?.nodes[nodeId];
      const cpuLoad = nodeTelemetry ? nodeTelemetry.cpu_percent / 100 : 0.45;

      const nodeObj = new THREE.Group();
      nodeObj.position.copy(pos);

      // Base Pedestal
      const baseGeo = new THREE.CylinderGeometry(0.85, 0.95, 0.45, 32);
      const baseMat = new THREE.MeshStandardMaterial({
        color: 0xf1f5f9,
        roughness: 0.3,
        metalness: 0.4,
      });
      const baseMesh = new THREE.Mesh(baseGeo, baseMat);
      (baseMesh as any).meta = {
        type: 'node',
        id: nodeId,
        label: `COMPUTE HOST: ${nodeId}`,
        metric: nodeTelemetry ? `CPU: ${nodeTelemetry.cpu_percent}% · RAM: ${nodeTelemetry.ram_percent}%` : 'HOST ONLINE'
      };
      nodeObj.add(baseMesh);
      interactableObjects.push(baseMesh);
      nodePedestals.push(baseMesh);

      // Status Ring
      const statusColor = nodeTelemetry?.status === 'online' ? 0x059669 : 0xd97706;
      const statusRingGeo = new THREE.TorusGeometry(0.88, 0.03, 16, 32);
      const statusRingMat = new THREE.MeshBasicMaterial({ color: statusColor });
      const statusRingMesh = new THREE.Mesh(statusRingGeo, statusRingMat);
      statusRingMesh.rotation.x = Math.PI / 2;
      statusRingMesh.position.y = 0.23;
      nodeObj.add(statusRingMesh);

      // CPU Load Column Indicator
      const colHeight = Math.max(0.2, cpuLoad * 1.2);
      const colGeo = new THREE.CylinderGeometry(0.35, 0.35, colHeight, 24);
      const colMat = new THREE.MeshStandardMaterial({
        color: cpuLoad > 0.8 ? 0xdc2626 : 0x2563eb,
        roughness: 0.2,
        metalness: 0.6,
        transparent: true,
        opacity: 0.85,
      });
      const colMesh = new THREE.Mesh(colGeo, colMat);
      colMesh.position.y = 0.23 + colHeight / 2;
      nodeObj.add(colMesh);

      clusterGroup.add(nodeObj);
    });

    // --- 3. Virtual Machines (Workloads) ---
    const vms = cluster && Object.keys(cluster.vms).length > 0
      ? Object.values(cluster.vms).slice(0, 6)
      : [
          { vmid: 'vm-101', name: 'billing-db', node_id: nodesList[0], cpu_percent: 62.0, sla_priority: 'critical' },
          { vmid: 'vm-102', name: 'api-gateway', node_id: nodesList[0], cpu_percent: 34.0, sla_priority: 'high' },
          { vmid: 'vm-103', name: 'redis-cache', node_id: nodesList[1], cpu_percent: 28.0, sla_priority: 'standard' },
          { vmid: 'vm-104', name: 'auth-service', node_id: nodesList[1], cpu_percent: 41.0, sla_priority: 'high' },
          { vmid: 'vm-105', name: 'analytics-worker', node_id: nodesList[2], cpu_percent: 55.0, sla_priority: 'batch' },
          { vmid: 'vm-106', name: 'cron-runner', node_id: nodesList[2], cpu_percent: 18.0, sla_priority: 'standard' }
        ];

    const vmObjects: { mesh: THREE.Mesh; baseAngle: number; radius: number; center: THREE.Vector3; id: string }[] = [];

    vms.forEach((vm, i) => {
      const parentNodeId = vm.node_id;
      const center = activeNodePos[parentNodeId] || defaultPositions[i % 3];

      const vmGeo = new THREE.BoxGeometry(0.32, 0.22, 0.32);
      const isCritical = vm.sla_priority === 'critical';
      const vmMat = new THREE.MeshStandardMaterial({
        color: isCritical ? 0x7c3aed : 0x0284c7,
        roughness: 0.25,
        metalness: 0.5,
      });
      const vmMesh = new THREE.Mesh(vmGeo, vmMat);
      (vmMesh as any).meta = {
        type: 'vm',
        id: vm.vmid,
        label: `VM: ${vm.name || vm.vmid}`,
        metric: `SLA: ${vm.sla_priority.toUpperCase()} · CPU: ${vm.cpu_percent}%`
      };

      const angle = (i % 2) * Math.PI + (i * 0.4);
      const radius = 1.35;
      vmMesh.position.set(
        center.x + Math.cos(angle) * radius,
        center.y + 0.5 + (i % 2) * 0.3,
        center.z + Math.sin(angle) * radius
      );

      interactableObjects.push(vmMesh);
      clusterGroup.add(vmMesh);

      vmObjects.push({
        mesh: vmMesh,
        baseAngle: angle,
        radius,
        center,
        id: vm.vmid
      });
    });

    // --- 4. Interconnect Conduits (Node -> AI Core) ---
    const splinePointsList: THREE.Vector3[][] = [];
    nodesList.forEach((nodeId) => {
      const nodePos = activeNodePos[nodeId];
      const midPoint = new THREE.Vector3(
        (nodePos.x + coreGroup.position.x) * 0.5,
        (nodePos.y + coreGroup.position.y) * 0.5 + 0.4,
        (nodePos.z + coreGroup.position.z) * 0.5 + 0.3
      );

      const curve = new THREE.QuadraticBezierCurve3(nodePos, midPoint, coreGroup.position);
      const pts = curve.getPoints(32);
      splinePointsList.push(pts);

      const lineGeo = new THREE.BufferGeometry().setFromPoints(pts);
      const lineMat = new THREE.LineBasicMaterial({
        color: 0x94a3b8,
        transparent: true,
        opacity: 0.3,
      });
      const line = new THREE.Line(lineGeo, lineMat);
      clusterGroup.add(line);
    });

    // --- 5. Telemetry Particle Stream along Conduits ---
    const particleCount = 72;
    const particleGeo = new THREE.BufferGeometry();
    const particlePositions = new Float32Array(particleCount * 3);
    const particleColors = new Float32Array(particleCount * 3);
    const particleOffsets: number[] = [];

    for (let i = 0; i < particleCount; i++) {
      particleOffsets.push(Math.random());
      const spline = splinePointsList[i % splinePointsList.length];
      const pt = spline[0];
      particlePositions[i * 3] = pt.x;
      particlePositions[i * 3 + 1] = pt.y;
      particlePositions[i * 3 + 2] = pt.z;

      // Electric blue / cyan tint
      particleColors[i * 3] = 0.15;
      particleColors[i * 3 + 1] = 0.4;
      particleColors[i * 3 + 2] = 0.95;
    }

    particleGeo.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3));
    particleGeo.setAttribute('color', new THREE.BufferAttribute(particleColors, 3));

    const particleMat = new THREE.PointsMaterial({
      size: 0.08,
      vertexColors: true,
      transparent: true,
      opacity: 0.85,
    });
    const particles = new THREE.Points(particleGeo, particleMat);
    clusterGroup.add(particles);

    // --- 6. Dynamic Migration Trajectory Arc ---
    let migrationArcLine: THREE.Line | null = null;
    let migrationParticle: THREE.Mesh | null = null;
    let migrationCurve: THREE.QuadraticBezierCurve3 | null = null;

    if (isMigrating) {
      const srcPos = activeNodePos[sourceNodeId] || defaultPositions[0];
      const tgtPos = activeNodePos[targetNodeId] || defaultPositions[1];
      const arcPeak = new THREE.Vector3(
        (srcPos.x + tgtPos.x) / 2,
        Math.max(srcPos.y, tgtPos.y) + 1.8,
        (srcPos.z + tgtPos.z) / 2 + 0.8
      );

      migrationCurve = new THREE.QuadraticBezierCurve3(srcPos, arcPeak, tgtPos);
      const arcPts = migrationCurve.getPoints(50);
      const arcGeo = new THREE.BufferGeometry().setFromPoints(arcPts);
      const arcMat = new THREE.LineBasicMaterial({
        color: 0x059669,
        linewidth: 2,
        transparent: true,
        opacity: 0.85,
      });
      migrationArcLine = new THREE.Line(arcGeo, arcMat);
      clusterGroup.add(migrationArcLine);

      // Glowing migration traveler
      const travelerGeo = new THREE.SphereGeometry(0.18, 16, 16);
      const travelerMat = new THREE.MeshStandardMaterial({
        color: 0x10b981,
        emissive: 0x059669,
        emissiveIntensity: 0.8,
      });
      migrationParticle = new THREE.Mesh(travelerGeo, travelerMat);
      (migrationParticle as any).meta = {
        type: 'vm',
        id: migratingVmId,
        label: `MIGRATING WORKLOAD: ${migratingVmId}`,
        metric: `ROUTE: ${sourceNodeId} → ${targetNodeId}`
      };
      interactableObjects.push(migrationParticle);
      clusterGroup.add(migrationParticle);
    }

    // --- Mouse Parallax & Raycasting ---
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2(-999, -999);
    let targetRotX = 0;
    let targetRotY = 0;

    const handlePointerMove = (event: MouseEvent) => {
      const rect = container.getBoundingClientRect();
      const x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      const y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
      mouse.x = x;
      mouse.y = y;

      if (!prefersReducedMotion) {
        targetRotY = x * 0.18;
        targetRotX = -y * 0.12;
      }
    };

    const handleClick = () => {
      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(interactableObjects, true);
      if (intersects.length > 0) {
        let obj: THREE.Object3D | null = intersects[0].object;
        while (obj && !(obj as any).meta) {
          obj = obj.parent;
        }
        if (obj && (obj as any).meta) {
          const meta = (obj as any).meta;
          if (meta.type === 'node' && onSelectNode) onSelectNode(meta.id);
          if (meta.type === 'vm' && onSelectVm) onSelectVm(meta.id);
        }
      }
    };

    container.addEventListener('pointermove', handlePointerMove);
    container.addEventListener('click', handleClick);

    // --- Window Scroll Modulation ---
    let scrollModulation = 0;
    const handleScroll = () => {
      const scrollY = window.scrollY || document.documentElement.scrollTop;
      scrollModulation = Math.min(scrollY / 800, 1.0);
    };
    window.addEventListener('scroll', handleScroll, { passive: true });

    // --- Resize Handler ---
    const handleResize = () => {
      if (!container) return;
      const w = container.clientWidth;
      const h = container.clientHeight || 520;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener('resize', handleResize);

    // --- Animation Loop ---
    let animationFrameId: number;
    let clock = new THREE.Clock();

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      const elapsed = clock.getElapsedTime();

      if (!prefersReducedMotion) {
        // Smooth camera parallax
        clusterGroup.rotation.y += (targetRotY - clusterGroup.rotation.y) * 0.04;
        clusterGroup.rotation.x += (targetRotX - clusterGroup.rotation.x) * 0.04;

        // Scroll modulation: tilt and pull back slightly
        camera.position.y = 3.2 - scrollModulation * 1.0;
        camera.position.z = 10.5 + scrollModulation * 2.5;

        // AI Core gentle breathing & rotation
        coreGroup.rotation.y = elapsed * 0.25;
        coreGroup.rotation.x = Math.sin(elapsed * 0.3) * 0.15;
        const pulse = 1.0 + Math.sin(elapsed * 2.0) * 0.04;
        coreMesh.scale.set(pulse, pulse, pulse);

        // Orbit VMs slowly around nodes
        vmObjects.forEach((vmObj, i) => {
          const currentAngle = vmObj.baseAngle + elapsed * (0.2 + (i % 3) * 0.05);
          vmObj.mesh.position.x = vmObj.center.x + Math.cos(currentAngle) * vmObj.radius;
          vmObj.mesh.position.z = vmObj.center.z + Math.sin(currentAngle) * vmObj.radius;
          vmObj.mesh.position.y = vmObj.center.y + 0.5 + Math.sin(elapsed * 1.5 + i) * 0.08;
          vmObj.mesh.rotation.y = elapsed * 0.5;
        });

        // Telemetry particles moving toward Core
        const positions = particleGeo.attributes.position.array as Float32Array;
        for (let i = 0; i < particleCount; i++) {
          particleOffsets[i] = (particleOffsets[i] + 0.006) % 1.0;
          const spline = splinePointsList[i % splinePointsList.length];
          const pointIdx = Math.floor(particleOffsets[i] * (spline.length - 1));
          const pt = spline[pointIdx];
          positions[i * 3] = pt.x;
          positions[i * 3 + 1] = pt.y;
          positions[i * 3 + 2] = pt.z;
        }
        particleGeo.attributes.position.needsUpdate = true;

        // Animate migration particle along arc
        if (migrationParticle && migrationCurve) {
          const migT = (elapsed * 0.35) % 1.0;
          const migPt = migrationCurve.getPoint(migT);
          migrationParticle.position.copy(migPt);
        }
      }

      // Raycasting for hover tooltip
      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(interactableObjects, true);
      if (intersects.length > 0) {
        let obj: THREE.Object3D | null = intersects[0].object;
        while (obj && !(obj as any).meta) {
          obj = obj.parent;
        }
        if (obj && (obj as any).meta) {
          const meta = (obj as any).meta;
          const vector = new THREE.Vector3();
          obj.getWorldPosition(vector);
          vector.project(camera);
          const screenX = ((vector.x + 1) * container.clientWidth) / 2;
          const screenY = ((-vector.y + 1) * container.clientHeight) / 2;

          setHoveredEntity({
            type: meta.type,
            id: meta.id,
            label: meta.label,
            metric: meta.metric,
            x: screenX,
            y: screenY,
          });
        }
      } else {
        setHoveredEntity(null);
      }

      renderer.render(scene, camera);
    };

    animate();

    // --- Cleanup & Disposal ---
    return () => {
      cancelAnimationFrame(animationFrameId);
      container.removeEventListener('pointermove', handlePointerMove);
      container.removeEventListener('click', handleClick);
      window.removeEventListener('scroll', handleScroll);
      window.removeEventListener('resize', handleResize);

      // Geometries
      coreGeo.dispose();
      wireGeo.dispose();
      ringGeo.dispose();
      particleGeo.dispose();

      // Materials
      coreMat.dispose();
      wireMat.dispose();
      ringMat.dispose();
      particleMat.dispose();

      if (renderer.domElement && container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, [cluster, isMigrating, sourceNodeId, targetNodeId, migratingVmId, onSelectNode, onSelectVm]);

  return (
    <div className="relative w-full h-[420px] sm:h-[480px] lg:h-[520px] rounded-2xl border border-[#E2E8F0] bg-gradient-to-b from-[#FFFFFF] via-[#F8FAFC] to-[#F1F5F9] shadow-sm overflow-hidden select-none">
      {/* Subtle architectural grid backdrop */}
      <div className="absolute inset-0 technical-grid-light opacity-50 pointer-events-none" />

      {/* 3D Canvas Mount */}
      <div ref={containerRef} className="absolute inset-0 cursor-grab active:cursor-grabbing" />

      {/* Interactive Tooltip Overlay */}
      {hoveredEntity && (
        <div
          className="pointer-events-none absolute z-20 transform -translate-x-1/2 -translate-y-full mb-3 rounded-lg border border-[#CBD5E1] bg-white/95 px-3 py-1.5 shadow-md backdrop-blur font-mono text-[11px] transition-all"
          style={{
            left: `${hoveredEntity.x}px`,
            top: `${hoveredEntity.y}px`,
          }}
        >
          <div className="font-bold text-[#0F172A]">{hoveredEntity.label}</div>
          {hoveredEntity.metric && (
            <div className="text-[#475569] text-[10px] mt-0.5">{hoveredEntity.metric}</div>
          )}
        </div>
      )}

      {/* 3D Legend & Controls Pill */}
      <div className="absolute bottom-3.5 left-4 z-10 flex flex-wrap items-center gap-2 font-mono text-[10px] text-[#64748B]">
        <div className="flex items-center space-x-1.5 rounded-full border border-[#E2E8F0] bg-white/90 px-3 py-1 shadow-sm">
          <span className="h-2 w-2 rounded-full bg-blue-600 animate-pulse" />
          <span className="font-semibold text-[#0F172A]">AI REASONING CORE</span>
        </div>
        <div className="flex items-center space-x-1.5 rounded-full border border-[#E2E8F0] bg-white/90 px-3 py-1 shadow-sm">
          <span className="h-2 w-2 rounded-full bg-emerald-600" />
          <span>COMPUTE HOSTS</span>
        </div>
        {isMigrating && (
          <div className="flex items-center space-x-1.5 rounded-full border border-emerald-300 bg-emerald-50 px-3 py-1 text-emerald-700 font-semibold shadow-sm animate-pulse">
            <span>ACTIVE MIGRATION CONDUIT</span>
          </div>
        )}
      </div>

      <div className="absolute top-3.5 right-4 z-10 font-mono text-[10px] text-[#94A3B8] hidden sm:block">
        POINTER PARALLAX · CLICK TO FOCUS
      </div>
    </div>
  );
};
