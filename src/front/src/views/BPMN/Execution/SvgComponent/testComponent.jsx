import { useState } from "react";

import LoadingButton from "@mui/lab/LoadingButton";
import LinearProgress from '@mui/material/LinearProgress';
import { Input } from "@mui/material";


const readFromRedis = async (key) => {
    const response = await fetch(`http://localhost:7379/GET/${key}`);
    const data = await response.json()
    return data["GET"]
}



const TestComponentV2 = ({processFunc, calcFunc}) => {
	const [testTimes, setTestTimes] = useState(0);
	const [testing, setTesting] = useState(false);
	const [processingNum, setProcessingNum] = useState(0);

	const testTime = async (processFunc) => {
        setTesting(true);
		const total_res = [];
		for (let i = 0; i < testTimes; i++) {
			const output_obj = await processFunc(readFromRedis)
            // get Executor log from redis
            const res = calcFunc({...output_obj});
			total_res.push(res);
            setProcessingNum(i);
		}
        // generate file and download
        const blob = new Blob([JSON.stringify(total_res)], { type: "text/plain" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "test_result.json";
        a.click();
        URL.revokeObjectURL(url);
        a.remove();
        setTesting(false);
	};

	return (
		<div>
			<Input placeholder="Input" onChange={(e)=>{
                setTestTimes(Number.parseInt(e.target.value))}} />
            {/* 进度条 */}
            {/* {testing?<LinearProgress value={Math.round(processingNum*100/testTimes)} />:null} */}
			{testing?
			<h5>{processingNum} / {testTimes}</h5>:null
			}
			<LoadingButton
				loading={testing}
				onClick={() => {
					testTime(processFunc);
				}}
			>
				Test
			</LoadingButton>
		</div>
	);
};

export default TestComponentV2;