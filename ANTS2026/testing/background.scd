// Background Layer - Mystic Ambient Pad Cloud
// Extracted from synth.scd Layer 1
//
// Usage:
// 1. Evaluate this entire file (Ctrl+A, then Ctrl+Enter)
// 2. Wait for "Background layer loaded" message
// 3. Pad will play continuously
//
// Stop: ~padPlayer.stop; s.freeAll;

// Configure server options
s.options.memSize = 8192 * 16;
s.options.numBuffers = 1024 * 16;

// Clean up any previous session
if(~padPlayer.notNil) { ~padPlayer.stop };
if(s.serverRunning) { s.freeAll };

s.waitForBoot({
	fork {
		// Extra safety: free all on boot
		s.freeAll;
		0.5.wait;

		// Global state
		~bpm = 80;
		~clock = TempoClock.new(~bpm/60);

		// Audio busses
		~fxBus = Bus.audio(s, 2);

		// Simple reverb+echo fx synth
		SynthDef.new("new_fx", { |inBus, out=0, mix=0.5, decay=4|
			var inSig = In.ar(inBus, 2);
			var rev = FreeVerb2.ar(inSig[0], inSig[1], mix, 0.9, decay);
			//var del = CombN.ar(inSig, 0.6, 0.45, 3);
			Out.ar(out, rev * 0.6);
		}).add;

		// Ambient pad synth - mystic, evolving
		SynthDef.new("pad_synth", { |outBus=0, freq=200, amp=0.2, pan=0|
			var osc, sig, detune, mod, env;
			// Long attack/release envelope for smooth morphing
			env = EnvGen.kr(Env.linen(8, 20, 12, 1, 'sine'), doneAction: 2);
			// Slow LFO modulation for movement
			mod = LFNoise1.kr(0.05).range(0.97, 1.03);
			detune = LFNoise1.kr(0.08).range(-0.2, 0.2);
			// Rich harmonic stack with detuning
			osc = Mix.new([
				SinOsc.ar(freq * 0.5 * mod, 0, 0.3),
				SinOsc.ar(freq * 0.501 + detune, 0, 0.25),
				Saw.ar(freq * 0.2 * mod, 0.15),
				Pulse.ar(freq * 0.06, LFNoise1.kr(0.1).range(0.3, 0.7), 0.12),
				SinOsc.ar(freq * 3.01 - detune, 0, 0.18),
				SinOsc.ar(freq , 0, 0.1)
			]);
			// Subtle chorus/shimmer effect
			sig = osc + DelayC.ar(osc, 0.05, LFNoise1.kr(0.2).range(0.01, 0.03), 0.4);
			sig = HPF.ar(sig, 40);
			sig = LPF.ar(sig, LFNoise1.kr(0.15).range(200, 800));
			// Deep reverb
			sig = FreeVerb.ar(sig, 0.95, 0.95, 0.7);
			// Stereo spread
			sig = sig + PitchShift.ar(sig, 0.2, LFNoise1.kr(0.3).range(0.998, 1.002), 0, 0.01);
			sig = Pan2.ar(sig * amp * env * 0.6, pan);
			Out.ar(outBus, sig);
		}).add;

		// Wait for all SynthDefs to be loaded
		s.sync;

		// Mystic ambient pad cloud - plays continuously
		~padPlayer = Routine({
			var freqs = [73.42, 110, 146.83, 220, 293.66];  // D2, A2, D3, A3, D4 - harmonics
			loop {
				var f = freqs.choose * rrand(0.98, 1.02);  // Choose harmonic with slight detune
				var p = rrand(-0.8, 0.8);  // Wide stereo field
				var a = rrand(0.12, 0.20);  // Varying amplitude
				Synth("pad_synth", [\outBus, ~fxBus.index, \freq, f, \amp, a, \pan, p]);
				// Irregular spawning timing for organic feel
				(~clock.beatsPerBar * [1.5, 2.0, 2.5, 3.0].choose).wait;
			}
		}).play(~clock);

		// FX instance - processes pad output
		Synth.after(s.defaultGroup, "new_fx", [\inBus, ~fxBus.index, \out, 0, \mix, 0.6, \decay, 6]);

		"Background layer loaded. Mystic pad playing continuously.".postln;
		"To stop: ~padPlayer.stop; s.freeAll;".postln;

	}; // end fork
}); // end waitForBoot


