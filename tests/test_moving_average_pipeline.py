import asyncio
import csv
from datetime import datetime, timezone

import h5py
import numpy as np
import pytest

from common.config import ChannelConfig, DaqConfig, LoggingConfig, TmsConfig
from common.protocol import decode_daq_data
from common.filtering import MovingAverage
from laptop.analysis import read_analysis_data
from laptop.logs import export_csv
from laptop.telemetry import TelemetryClient
from pi.daq import DaqBlock, SimulatedDaqSource
from pi.logger import Hdf5SessionLogger, SessionMetadata
from pi.telemetry import TelemetryServer
from pi.tms_agent import TmsAgent


def config(tmp_path):
    return TmsConfig(daq=DaqConfig(sample_rate=1000, block_ms=10),
        thrust=ChannelConfig(0, .5, -1.), pressure=ChannelConfig(1, .1, 2.),
        logging=LoggingConfig(directory=tmp_path))


def create_log(tmp_path):
    logger=Hdf5SessionLogger(config(tmp_path))
    path=logger.open(SessionMetadata('MA_PIPELINE','ma1234',datetime.now(timezone.utc).isoformat()))
    for i in range(12):
        raw=np.column_stack([np.arange(i*10,i*10+10), np.arange(i*10,i*10+10)*2]).astype(np.int16)
        logger.append_block(DaqBlock(i,i*10,1000,(0,1),raw))
    logger.close()
    return path


@pytest.mark.parametrize('legacy', [False, True])
def test_csv_hdf5_and_analysis_use_same_ma80_across_chunks(tmp_path, legacy):
    path=create_log(tmp_path)
    if legacy:
        with h5py.File(path,'r+') as data:
            del data['samples/thrust_N_ma']
            del data['samples/pressure_bar_ma']
            del data['metadata'].attrs['moving_average_window_samples']
    csv_path=export_csv(path,tmp_path/'ma.csv',chunk_samples=7)
    a=read_analysis_data(path)
    b=read_analysis_data(csv_path)
    with h5py.File(path) as data:
        indices=data['samples/sample_index'][:]
        expected=MovingAverage().apply_indexed(data['samples/thrust_N'][:],indices)
    np.testing.assert_allclose(a.thrust_N,expected,atol=1e-6)
    np.testing.assert_array_equal(a.thrust_N,b.thrust_N)
    np.testing.assert_array_equal(a.pressure_bar,b.pressure_bar)
    with csv_path.open() as stream:
        rows=list(csv.DictReader(stream))
    assert all(row['moving_average_window_samples']=='80' for row in rows)
    assert float(rows[79]['thrust_N_ma']) == pytest.approx(expected[79])


def test_original_csv_without_filter_gets_ma_not_lpf(tmp_path):
    path=tmp_path/'old.csv'
    path.write_text('sample_index,time_s,thrust_N,pressure_bar,thrust_N_lpf\n0,0,0,2,90\n1,.001,100,4,95\n')
    data=read_analysis_data(path)
    np.testing.assert_equal(data.thrust_N,[0,50])
    np.testing.assert_equal(data.pressure_bar,[2,3])


def test_late_clients_and_logger_share_acquisition_filter_values(tmp_path):
    async def scenario():
        c=config(tmp_path)
        agent=TmsAgent(c,SimulatedDaqSource(c.daq,(0,1),realtime=True))
        server=TelemetryServer(agent,c,port=0)
        await server.start()
        first, late=TelemetryClient(), TelemetryClient()
        path=None
        try:
            await first.connect(port=server.port)
            result=await first.start_session('MA_SHARED')
            path=tmp_path/result['log_file']
            await asyncio.sleep(.15)  # Late client has no window history.
            await late.connect(port=server.port)
            blocks=[]
            for _ in range(2):
                blocks.append(await late.wait_for_fresh_block(timeout=2))
            await first.stop_session()
            with h5py.File(path) as data:
                saved=np.column_stack([data['samples/thrust_N_ma'][:],data['samples/pressure_bar_ma'][:]])
                for block in blocks:
                    np.testing.assert_array_equal(block.values,saved[block.first_sample_index:block.first_sample_index+block.sample_count])
                assert data['metadata'].attrs['moving_average_window_samples']==80
        finally:
            if agent.state.value in ('RECORDING','TRIGGERED'):
                await asyncio.to_thread(agent.stop_session)
            await first.disconnect()
            await late.disconnect()
            await server.close()
    asyncio.run(scenario())
